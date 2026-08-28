from decimal import Decimal
from uuid import UUID

import stripe

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.logging import get_logger
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.schemas.payment import CheckoutSessionResponse, StripeWebhookResponse

logger = get_logger(__name__)


class StripePaymentService:
    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    def create_checkout_session(
        self,
        order_id: UUID,
        *,
        current_user: User,
    ) -> CheckoutSessionResponse:
        settings = get_settings()
        self._ensure_stripe_configured(settings)

        order = self._orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if order.user_id != current_user.id:
            raise BadRequestError("You can only pay for your own orders")
        if order.status is not OrderStatus.PENDING:
            raise BadRequestError("Only pending orders can be paid")

        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode="payment",
            customer_email=current_user.email,
            line_items=self._build_stripe_line_items(order, settings),
            success_url=(
                f"{settings.STRIPE_SUCCESS_URL.rstrip('/')}"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=settings.STRIPE_CANCEL_URL,
            metadata={"order_id": str(order.id)},
        )

        self._orders.set_checkout_session(order, session_id=session.id)
        logger.info("Created Stripe checkout session %s for order %s", session.id, order.id)

        return CheckoutSessionResponse(
            message="Checkout session created successfully",
            checkout_url=session.url,
            session_id=session.id,
        )

    def handle_webhook(
        self,
        payload: bytes,
        signature: str | None,
    ) -> StripeWebhookResponse:
        settings = get_settings()
        self._ensure_stripe_configured(settings)
        if not settings.STRIPE_WEBHOOK_SECRET.strip():
            raise BadRequestError("Stripe webhook secret is not configured")

        if not signature:
            raise BadRequestError("Missing Stripe-Signature header")

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError as exc:
            raise BadRequestError("Invalid webhook payload") from exc
        except stripe.SignatureVerificationError as exc:
            raise BadRequestError("Invalid Stripe webhook signature") from exc

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            self._mark_order_paid_from_session(session)
        elif event["type"] == "payment_intent.succeeded":
            intent = event["data"]["object"]
            self._mark_order_paid_from_payment_intent(intent)

        return StripeWebhookResponse(message="Webhook received")

    def charge_order_with_payment_method(
        self,
        order: Order,
        *,
        payment_method_id: str,
        customer_email: str,
    ) -> Order:
        settings = get_settings()
        self._ensure_stripe_configured(settings)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            intent = stripe.PaymentIntent.create(
                amount=_to_cents(order.total),
                currency=settings.STRIPE_CURRENCY,
                payment_method=payment_method_id,
                confirm=True,
                receipt_email=customer_email,
                metadata={"order_id": str(order.id)},
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never",
                },
            )
        except stripe.CardError as exc:
            logger.warning("Stripe card error for order %s: %s", order.id, exc.user_message)
            raise BadRequestError(exc.user_message or "Payment failed") from exc
        except stripe.StripeError as exc:
            logger.warning("Stripe error for order %s: %s", order.id, exc)
            raise BadRequestError("Payment failed") from exc

        if intent.status == "succeeded":
            paid = self._orders.update_payment_details(
                order,
                status=OrderStatus.PAID,
                payment_intent_id=intent.id,
                payment_method_id=payment_method_id,
            )
            logger.info("Charged order %s with payment intent %s", order.id, intent.id)
            return paid

        self._orders.update_payment_details(
            order,
            payment_intent_id=intent.id,
            payment_method_id=payment_method_id,
        )
        raise BadRequestError(f"Payment requires action or failed: {intent.status}")

    def _mark_order_paid_from_session(self, session: dict) -> None:
        order_id_raw = session.get("metadata", {}).get("order_id")
        session_id = session.get("id")

        order: Order | None = None
        if order_id_raw:
            try:
                order = self._orders.get_by_id(UUID(order_id_raw))
            except ValueError:
                order = None

        if order is None and session_id:
            order = self._orders.get_by_checkout_session_id(session_id)

        if order is None:
            logger.warning("Stripe webhook could not match order for session %s", session_id)
            return

        if order.status is OrderStatus.PAID:
            return

        if order.status is not OrderStatus.PENDING:
            logger.warning(
                "Stripe webhook ignored for order %s with status %s",
                order.id,
                order.status,
            )
            return

        self._orders.update_status(order, status=OrderStatus.PAID)
        logger.info("Marked order %s as PAID from Stripe webhook", order.id)

    def _mark_order_paid_from_payment_intent(self, intent: dict) -> None:
        order_id_raw = intent.get("metadata", {}).get("order_id")
        payment_intent_id = intent.get("id")
        payment_method_id = intent.get("payment_method")

        order: Order | None = None
        if order_id_raw:
            try:
                order = self._orders.get_by_id(UUID(order_id_raw))
            except ValueError:
                order = None

        if order is None and payment_intent_id:
            order = self._orders.get_by_payment_intent_id(payment_intent_id)

        if order is None:
            logger.warning(
                "Stripe webhook could not match order for payment intent %s",
                payment_intent_id,
            )
            return

        if order.status is OrderStatus.PAID:
            return

        if order.status is not OrderStatus.PENDING:
            logger.warning(
                "Stripe webhook ignored for order %s with status %s",
                order.id,
                order.status,
            )
            return

        self._orders.update_payment_details(
            order,
            status=OrderStatus.PAID,
            payment_intent_id=payment_intent_id,
            payment_method_id=payment_method_id,
        )
        logger.info("Marked order %s as PAID from payment intent webhook", order.id)

    def _build_stripe_line_items(self, order: Order, settings) -> list[dict]:
        return [
            {
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "product_data": {"name": item.product.name},
                    "unit_amount": _to_cents(item.unit_price),
                },
                "quantity": item.quantity,
            }
            for item in order.items
        ]

    def _ensure_stripe_configured(self, settings) -> None:
        if not settings.stripe_enabled:
            raise BadRequestError("Stripe is not configured")


def _to_cents(amount: Decimal) -> int:
    return int(amount * 100)
