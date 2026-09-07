from decimal import Decimal
from uuid import UUID

import stripe

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.logging import get_logger
from app.helpers.stripe_fee import round_money
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.schemas.payment import (
    CheckoutSessionResponse,
    PaymentConfigResponse,
    SavedCardListResponse,
    SavedCardRead,
    SetupIntentResponse,
    StripeWebhookResponse,
)

logger = get_logger(__name__)


class StripePaymentService:
    def __init__(self, orders: OrderRepository, users: UserRepository) -> None:
        self._orders = orders
        self._users = users

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
        customer_id = self.get_or_create_customer(current_user)
        session = stripe.checkout.Session.create(
            mode="payment",
            customer=customer_id,
            line_items=self._build_stripe_line_items(order, settings),
            success_url=(
                f"{settings.STRIPE_SUCCESS_URL.rstrip('/')}"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=settings.STRIPE_CANCEL_URL,
            metadata={"order_id": str(order.id), "user_id": str(current_user.id)},
            payment_intent_data={
                "setup_future_usage": "off_session",
                "metadata": {
                    "order_id": str(order.id),
                    "user_id": str(current_user.id),
                },
            },
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

    def payment_config(self) -> PaymentConfigResponse:
        settings = get_settings()
        self._ensure_stripe_configured(settings)
        if not settings.STRIPE_PUBLISHABLE_KEY.strip():
            raise BadRequestError("Stripe publishable key is not configured")
        return PaymentConfigResponse(publishable_key=settings.STRIPE_PUBLISHABLE_KEY.strip())

    def create_setup_intent(self, current_user: User) -> SetupIntentResponse:
        settings = get_settings()
        self._ensure_stripe_configured(settings)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        customer_id = self.get_or_create_customer(current_user)
        try:
            intent = stripe.SetupIntent.create(
                customer=customer_id,
                automatic_payment_methods={"enabled": True},
                usage="off_session",
                metadata={"user_id": str(current_user.id)},
            )
        except stripe.StripeError as exc:
            logger.warning("Stripe setup intent failed for user %s: %s", current_user.id, exc)
            raise BadRequestError("Could not start card setup") from exc
        if not intent.client_secret:
            raise BadRequestError("Could not start card setup")
        return SetupIntentResponse(
            message="Setup intent created successfully",
            client_secret=intent.client_secret,
        )

    def list_saved_cards(self, current_user: User) -> SavedCardListResponse:
        settings = get_settings()
        self._ensure_stripe_configured(settings)
        if not current_user.stripe_customer_id:
            return SavedCardListResponse(message="Saved cards", data=[])
        stripe.api_key = settings.STRIPE_SECRET_KEY
        cards: list[SavedCardRead] = []
        try:
            for method_type in ("card", "us_bank_account"):
                methods = stripe.PaymentMethod.list(
                    customer=current_user.stripe_customer_id,
                    type=method_type,
                    limit=20,
                )
                for method in methods.data:
                    saved = _saved_method_read(method)
                    if saved is not None:
                        cards.append(saved)
        except stripe.StripeError as exc:
            logger.warning("Stripe list cards failed for user %s: %s", current_user.id, exc)
            raise BadRequestError("Could not load saved cards") from exc

        return SavedCardListResponse(message="Saved payment methods", data=cards)

    def detach_saved_card(self, current_user: User, payment_method_id: str) -> SavedCardListResponse:
        self._assert_owned_payment_method(current_user, payment_method_id)
        settings = get_settings()
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            stripe.PaymentMethod.detach(payment_method_id)
        except stripe.StripeError as exc:
            logger.warning("Stripe detach card failed for user %s: %s", current_user.id, exc)
            raise BadRequestError("Could not remove that card") from exc
        return self.list_saved_cards(current_user)

    def get_or_create_customer(self, user: User) -> str:
        settings = get_settings()
        self._ensure_stripe_configured(settings)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        if user.stripe_customer_id:
            return user.stripe_customer_id
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={"user_id": str(user.id)},
            )
        except stripe.StripeError as exc:
            logger.warning("Stripe customer create failed for user %s: %s", user.id, exc)
            raise BadRequestError("Could not create a Stripe customer") from exc
        self._users.set_stripe_customer_id(user, customer.id)
        logger.info("Created Stripe customer for user %s", user.id)
        return customer.id

    def _assert_owned_payment_method(self, user: User, payment_method_id: str) -> None:
        settings = get_settings()
        stripe.api_key = settings.STRIPE_SECRET_KEY
        payment_method_id = _normalize_payment_method_id(payment_method_id)
        customer_id = self.get_or_create_customer(user)
        try:
            method = stripe.PaymentMethod.retrieve(payment_method_id)
        except stripe.StripeError as exc:
            raise BadRequestError("Payment method is invalid") from exc
        owner = _stripe_customer_id(method.customer)
        if owner and owner != customer_id:
            raise BadRequestError("This card does not belong to your account")
        if not owner:
            try:
                stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
            except stripe.StripeError as exc:
                raise BadRequestError("Could not save this card to your account") from exc

    def charge_order_with_payment_method(
        self,
        order: Order,
        *,
        payment_method_id: str,
        current_user: User,
    ) -> Order:
        settings = get_settings()
        self._ensure_stripe_configured(settings)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        payment_method_id = _normalize_payment_method_id(payment_method_id)
        self._assert_owned_payment_method(current_user, payment_method_id)
        customer_id = self.get_or_create_customer(current_user)
        try:
            intent = stripe.PaymentIntent.create(
                amount=_to_cents(order.total),
                currency=settings.STRIPE_CURRENCY,
                customer=customer_id,
                payment_method=payment_method_id,
                confirm=True,
                off_session=False,
                setup_future_usage="off_session",
                receipt_email=current_user.email,
                metadata={"order_id": str(order.id), "user_id": str(current_user.id)},
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

        amount_total = session.get("amount_total")
        if amount_total is not None and int(amount_total) != _to_cents(order.total):
            logger.error(
                "Stripe session amount mismatch for order %s "
                "(session=%s, order_cents=%s)",
                order.id,
                amount_total,
                _to_cents(order.total),
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

        amount = intent.get("amount")
        if amount is not None and int(amount) != _to_cents(order.total):
            logger.error(
                "Stripe payment intent amount mismatch for order %s "
                "(intent=%s, order_cents=%s)",
                order.id,
                amount,
                _to_cents(order.total),
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
        line_items = [
            {
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "product_data": {
                        "name": (
                            f"{item.product.name} ({item.variant_name})"
                            if item.variant_name
                            else item.product.name
                        )
                    },
                    "unit_amount": _to_cents(item.unit_price),
                },
                "quantity": item.quantity,
            }
            for item in order.items
        ]
        if order.stripe_fee and order.stripe_fee > 0:
            line_items.append(
                {
                    "price_data": {
                        "currency": settings.STRIPE_CURRENCY,
                        "product_data": {"name": "Stripe processing fee"},
                        "unit_amount": _to_cents(order.stripe_fee),
                    },
                    "quantity": 1,
                }
            )
        return line_items

    def _ensure_stripe_configured(self, settings) -> None:
        if not settings.stripe_enabled:
            raise BadRequestError("Stripe is not configured")


def _to_cents(amount: Decimal) -> int:
    return int(round_money(amount) * 100)


def _normalize_payment_method_id(payment_method_id: str) -> str:
    value = payment_method_id.strip()
    if not value.startswith("pm_") or len(value) < 6:
        raise BadRequestError("Payment method is invalid")
    return value


def _stripe_customer_id(customer: object) -> str | None:
    if customer is None:
        return None
    if isinstance(customer, str):
        return customer
    return getattr(customer, "id", None)


def _saved_method_read(method: object) -> SavedCardRead | None:
    method_type = getattr(method, "type", None)
    if not isinstance(method_type, str):
        method_type = "card"
    if method_type == "us_bank_account":
        bank = getattr(method, "us_bank_account", None)
        if bank is None:
            return None
        return SavedCardRead(
            id=getattr(method, "id"),
            brand=getattr(bank, "bank_name", None) or "Bank",
            last4=getattr(bank, "last4", None) or "****",
            exp_month=0,
            exp_year=0,
            type=method_type,
        )
    card = getattr(method, "card", None)
    if card is None:
        return None
    return SavedCardRead(
        id=getattr(method, "id"),
        brand=getattr(card, "brand", None) or "card",
        last4=getattr(card, "last4", None) or "****",
        exp_month=int(getattr(card, "exp_month", None) or 0),
        exp_year=int(getattr(card, "exp_year", None) or 0),
        type="card",
    )
