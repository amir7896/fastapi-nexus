from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.helpers.order_emails import send_order_email
from app.helpers.pricing import resolve_unit_price
from app.helpers.refund_policy import (
    RETURN_WINDOW_DAYS,
    cancel_refund_amount,
    return_refund_amount,
)
from app.helpers.stripe_fee import breakdown_with_stripe_fee
from app.helpers.tracking import build_tracking_url, canonicalize_carrier
from app.models.order import Order, OrderItem, OrderStatus, ReturnStatus
from app.models.user import User, UserRole
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.product_variant_repository import ProductVariantRepository
from app.schemas.order import (
    OrderCreateRequest,
    OrderItemRead,
    OrderListResponse,
    OrderRead,
    OrderResponse,
    OrderStatusUpdateRequest,
    OrderSummaryRead,
    ReturnRequestCreate,
    ReturnRequestRead,
    ReturnReviewRequest,
)
from app.schemas.shipping import ShippingAddressRead, ShippingAddressRequest
from app.schemas.pagination import PaginationQuery, build_pagination_meta
from app.services.email_service import EmailService
from app.services.notification_hub import notify_order_status
from app.services.stripe_payment_service import StripePaymentService

logger = get_logger(__name__)

_ADMIN_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: set(),
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.RETURNED: set(),
}

_CUSTOMER_CANCEL_STATUSES = {OrderStatus.PENDING, OrderStatus.PAID}


class OrderService:
    def __init__(
        self,
        orders: OrderRepository,
        products: ProductRepository,
        variants: ProductVariantRepository,
        stripe_payments: StripePaymentService,
        emails: EmailService | None = None,
    ) -> None:
        self._orders = orders
        self._products = products
        self._variants = variants
        self._stripe_payments = stripe_payments
        self._emails = emails or EmailService()

    def list_orders(
        self,
        pagination: PaginationQuery,
        *,
        current_user: User,
        status: OrderStatus | None = None,
        return_status: ReturnStatus | None = None,
        all_users: bool = False,
    ) -> OrderListResponse:
        self._auto_deliver_stale()
        if all_users:
            if current_user.role is not UserRole.ADMIN:
                raise ForbiddenError("Admin access required")
            user_filter = None
        else:
            user_filter = current_user.id
        items, total = self._orders.list_paginated(
            page=pagination.page,
            limit=pagination.limit,
            user_id=user_filter,
            status=status,
            return_status=return_status,
            search=pagination.search,
        )
        return OrderListResponse(
            message="Orders fetched successfully",
            data=[self._to_summary(order) for order in items],
            meta=build_pagination_meta(
                total=total,
                page=pagination.page,
                limit=pagination.limit,
            ),
        )

    def get_order(self, order_id: UUID, *, current_user: User) -> OrderResponse:
        self._auto_deliver_stale()
        order = self._get_accessible_order(order_id, current_user=current_user)
        return OrderResponse(
            message="Order fetched successfully",
            order=self._to_order_read(order),
        )

    def create_order(
        self,
        payload: OrderCreateRequest,
        *,
        current_user: User,
    ) -> OrderResponse:
        line_items = self._build_line_items(payload)
        self._reserve_stock(line_items)
        order: Order | None = None
        try:
            items_subtotal = sum(
                (item["subtotal"] for item in line_items),
                Decimal("0"),
            )
            settings = get_settings()
            pricing = breakdown_with_stripe_fee(
                items_subtotal,
                percent=settings.STRIPE_FEE_PERCENT,
                fixed=settings.STRIPE_FEE_FIXED,
            )
            order = self._orders.create(
                user_id=current_user.id,
                line_items=line_items,
                subtotal=pricing.subtotal,
                stripe_fee=pricing.fee,
                total=pricing.total,
                shipping=_shipping_dict(payload.shipping),
            )
            order = self._stripe_payments.charge_order_with_payment_method(
                order,
                payment_method_id=payload.payment_method_id,
                current_user=current_user,
            )
        except BadRequestError as exc:
            # Customer may finish payment later (Checkout / 3DS); keep stock reserved.
            if order is not None and "requires action" in exc.message.lower():
                raise
            self._release_stock(line_items)
            if order is not None and order.status is OrderStatus.PENDING:
                self._orders.update_status(order, status=OrderStatus.CANCELLED)
            raise
        except Exception:
            self._release_stock(line_items)
            if order is not None and order.status is OrderStatus.PENDING:
                self._orders.update_status(order, status=OrderStatus.CANCELLED)
            raise

        logger.info("Created order %s for user %s", order.id, current_user.id)
        if order.status is OrderStatus.PAID:
            self._notify(order)
            send_order_email(order, event="paid", emails=self._emails)
        message = (
            "Order created and paid successfully"
            if order.status is OrderStatus.PAID
            else "Order created successfully"
        )
        return OrderResponse(
            message=message,
            order=self._to_order_read(order),
        )

    def pay_order(
        self,
        order_id: UUID,
        *,
        payment_method_id: str,
        current_user: User,
        shipping: ShippingAddressRequest | None = None,
    ) -> OrderResponse:
        order = self._get_order(order_id)
        if order.user_id != current_user.id:
            raise BadRequestError("You can only pay for your own orders")
        if order.status is not OrderStatus.PENDING:
            raise BadRequestError("Only pending orders can be paid")
        if shipping is not None:
            order = self._orders.set_shipping(order, shipping=_shipping_dict(shipping))
        elif not order.shipping_name:
            raise BadRequestError("Shipping address is required before payment")
        paid = self._stripe_payments.charge_order_with_payment_method(
            order,
            payment_method_id=payment_method_id,
            current_user=current_user,
        )
        if paid.status is OrderStatus.PAID:
            self._notify(paid)
            send_order_email(paid, event="paid", emails=self._emails)
        return OrderResponse(
            message="Order paid successfully",
            order=self._to_order_read(paid),
        )

    def update_order_status(
        self,
        order_id: UUID,
        payload: OrderStatusUpdateRequest,
    ) -> OrderResponse:
        if payload.status is OrderStatus.DELIVERED:
            raise BadRequestError("The customer marks this order as received")
        if payload.status is OrderStatus.RETURNED:
            raise BadRequestError("Approve a return request to mark an order returned")

        order = self._get_order(order_id)
        previous_status = order.status
        self._ensure_status_transition(previous_status, payload.status)

        if payload.status is OrderStatus.CANCELLED:
            return self._cancel_order(order, previous_status=previous_status)

        carrier = None
        shipped_at = None
        if payload.status is OrderStatus.SHIPPED:
            try:
                carrier = canonicalize_carrier(payload.shipping_carrier)
            except ValueError as exc:
                raise BadRequestError(
                    "Carrier must be UPS, USPS, FedEx, DHL, TCS, Leopard, Pakistan Post, or Other"
                ) from exc
            shipped_at = datetime.now(timezone.utc)

        updated = self._orders.update_status(
            order,
            status=payload.status,
            tracking_number=payload.tracking_number,
            shipping_carrier=carrier,
            shipped_at=shipped_at,
        )
        logger.info("Updated order %s status to %s", updated.id, updated.status)
        self._notify(updated)
        if updated.status is OrderStatus.SHIPPED:
            send_order_email(updated, event="shipped", emails=self._emails)
        return OrderResponse(
            message="Order status updated successfully",
            order=self._to_order_read(updated),
        )

    def confirm_received(self, order_id: UUID, *, current_user: User) -> OrderResponse:
        order = self._get_accessible_order(order_id, current_user=current_user)
        if order.user_id != current_user.id:
            raise ForbiddenError("Only the customer can mark this order received")
        return self._deliver_order(order, actor="customer")

    def admin_confirm_received(self, order_id: UUID) -> OrderResponse:
        order = self._get_order(order_id)
        return self._deliver_order(order, actor="admin")

    def cancel_own_order(self, order_id: UUID, *, current_user: User) -> OrderResponse:
        order = self._get_accessible_order(order_id, current_user=current_user)
        if order.user_id != current_user.id:
            raise ForbiddenError("You can only cancel your own orders")
        if order.status not in _CUSTOMER_CANCEL_STATUSES:
            raise BadRequestError("You can only cancel before the order is processed")
        return self._cancel_order(order, previous_status=order.status)

    def request_return(
        self,
        order_id: UUID,
        payload: ReturnRequestCreate,
        *,
        current_user: User,
    ) -> OrderResponse:
        order = self._get_accessible_order(order_id, current_user=current_user)
        if order.user_id != current_user.id:
            raise ForbiddenError("You can only return your own orders")
        if order.status is not OrderStatus.DELIVERED:
            raise BadRequestError("Returns are only available after you mark the order received")
        if order.return_status == ReturnStatus.PENDING.value:
            raise BadRequestError("A return request is already pending")
        if order.return_status == ReturnStatus.APPROVED.value or order.status is OrderStatus.RETURNED:
            raise BadRequestError("This order was already returned")
        if return_refund_amount(order) <= 0:
            raise BadRequestError("There is nothing left to refund on this order")
        delivered_at = order.delivered_at or order.updated_at
        if delivered_at.tzinfo is None:
            delivered_at = delivered_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - delivered_at > timedelta(days=RETURN_WINDOW_DAYS):
            raise BadRequestError(f"The {RETURN_WINDOW_DAYS}-day return window has closed")

        order.return_status = ReturnStatus.PENDING.value
        order.return_reason = payload.reason.strip()
        order.return_details = (payload.details or "").strip() or None
        order.return_admin_note = None
        updated = self._orders.save(order)
        return OrderResponse(
            message="Return request submitted",
            order=self._to_order_read(updated),
        )

    def review_return(
        self,
        order_id: UUID,
        payload: ReturnReviewRequest,
    ) -> OrderResponse:
        if payload.decision not in {ReturnStatus.APPROVED, ReturnStatus.REJECTED}:
            raise BadRequestError("Decision must be APPROVED or REJECTED")
        order = self._get_order(order_id)
        if order.return_status != ReturnStatus.PENDING.value:
            raise BadRequestError("There is no pending return request")
        if payload.decision is ReturnStatus.REJECTED:
            order.return_status = ReturnStatus.REJECTED.value
            order.return_admin_note = (payload.admin_note or "").strip() or None
            updated = self._orders.save(order)
            send_order_email(updated, event="return_rejected", emails=self._emails)
            return OrderResponse(
                message="Return request rejected",
                order=self._to_order_read(updated),
            )

        amount = return_refund_amount(order)
        refund_id = self._refund_if_needed(order, amount)
        order.return_status = ReturnStatus.APPROVED.value
        order.return_admin_note = (payload.admin_note or "").strip() or None
        order.status = OrderStatus.RETURNED
        order.amount_refunded = (order.amount_refunded or Decimal("0")) + amount
        order.refunded_at = datetime.now(timezone.utc)
        if refund_id:
            order.stripe_refund_id = refund_id
        self._restore_order_stock(order)
        updated = self._orders.save(order)
        logger.info("Approved return and refunded %s on order %s", amount, updated.id)
        self._notify(updated)
        send_order_email(updated, event="return_approved", emails=self._emails)
        return OrderResponse(
            message="Return approved and refunded",
            order=self._to_order_read(updated),
        )

    def _build_line_items(self, payload: OrderCreateRequest) -> list[dict]:
        seen_keys: set[tuple[UUID, UUID | None]] = set()
        line_items: list[dict] = []

        for item in payload.items:
            key = (item.product_id, item.variant_id)
            if key in seen_keys:
                raise BadRequestError("Duplicate product/variant in order items")
            seen_keys.add(key)

            product = self._products.get_by_id(item.product_id)
            if product is None:
                raise NotFoundError(f"Product not found: {item.product_id}")

            has_variants = bool(product.variants)
            if has_variants and item.variant_id is None:
                raise BadRequestError(
                    f"variantId is required for product '{product.name}'"
                )
            if not has_variants and item.variant_id is not None:
                raise BadRequestError(
                    f"Product '{product.name}' has no variants"
                )

            variant = None
            variant_name = None
            display_name = product.name
            if item.variant_id is not None:
                variant = self._variants.get_by_id(item.variant_id)
                if variant is None or variant.product_id != product.id:
                    raise NotFoundError(f"Variant not found: {item.variant_id}")
                variant_name = variant.name or None
                display_name = (
                    f"{product.name} ({variant.name})" if variant.name else product.name
                )
                available = variant.stock
            else:
                available = product.stock

            if available < item.quantity:
                raise BadRequestError(
                    f"Insufficient stock for '{display_name}' "
                    f"(available: {available}, requested: {item.quantity})"
                )

            unit_price = resolve_unit_price(product, variant)
            line_items.append(
                {
                    "product_id": item.product_id,
                    "variant_id": item.variant_id,
                    "product_name": display_name,
                    "variant_name": variant_name,
                    "quantity": item.quantity,
                    "unit_price": unit_price,
                    "subtotal": unit_price * item.quantity,
                }
            )

        return line_items

    def _reserve_stock(self, line_items: list[dict]) -> None:
        reserved: list[dict] = []
        try:
            for item in line_items:
                if item["variant_id"] is not None:
                    ok = self._variants.decrement_stock(
                        item["variant_id"], item["quantity"]
                    )
                else:
                    ok = self._products.decrement_stock(
                        item["product_id"], item["quantity"]
                    )
                if not ok:
                    raise BadRequestError(
                        f"Insufficient stock for '{item['product_name']}' "
                        f"(requested: {item['quantity']})"
                    )
                reserved.append(item)
                if item["variant_id"] is not None:
                    self._sync_product_stock(item["product_id"])
        except Exception:
            self._release_stock(reserved)
            raise

    def _release_stock(self, line_items: list[dict]) -> None:
        for item in line_items:
            if item["variant_id"] is not None:
                self._variants.increment_stock(item["variant_id"], item["quantity"])
                self._sync_product_stock(item["product_id"])
            else:
                self._products.increment_stock(item["product_id"], item["quantity"])

    def _restore_order_stock(self, order: Order) -> None:
        line_items = [
            {
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "quantity": item.quantity,
            }
            for item in order.items
        ]
        self._release_stock(line_items)

    def _sync_product_stock(self, product_id: UUID) -> None:
        product = self._products.get_by_id(product_id, include_deleted=True)
        if product is None:
            return
        if self._variants.count_by_product(product_id) == 0:
            return
        total = self._variants.sum_stock_by_product(product_id)
        self._products.update(
            product,
            name=product.name,
            description=product.description,
            brand_id=product.brand_id,
            sku=product.sku,
            price=product.price,
            price_sale=product.price_sale,
            colors=list(product.colors or []),
            status=product.status or "",
            stock=total,
            category_id=product.category_id,
        )

    def _cancel_order(self, order: Order, *, previous_status: OrderStatus) -> OrderResponse:
        amount = cancel_refund_amount(order)
        refund_id = self._refund_if_needed(order, amount)
        order.status = OrderStatus.CANCELLED
        if refund_id:
            order.amount_refunded = (order.amount_refunded or Decimal("0")) + amount
            order.refunded_at = datetime.now(timezone.utc)
            order.stripe_refund_id = refund_id
        if previous_status in {
            OrderStatus.PENDING,
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
        }:
            self._restore_order_stock(order)
        updated = self._orders.save(order)
        logger.info("Cancelled order %s and refunded %s", updated.id, amount)
        self._notify(updated)
        send_order_email(updated, event="cancelled", emails=self._emails)
        return OrderResponse(
            message="Order cancelled successfully",
            order=self._to_order_read(updated),
        )

    def _refund_if_needed(self, order: Order, amount: Decimal) -> str | None:
        if amount <= 0:
            return None
        if not order.stripe_payment_intent_id:
            return None
        return self._stripe_payments.refund_payment_intent(
            payment_intent_id=order.stripe_payment_intent_id,
            amount=amount,
        )

    def _deliver_order(self, order: Order, *, actor: str) -> OrderResponse:
        if order.status is not OrderStatus.SHIPPED:
            raise BadRequestError("Only shipped orders can be marked received")
        order.status = OrderStatus.DELIVERED
        order.delivered_at = datetime.now(timezone.utc)
        updated = self._orders.save(order)
        logger.info("%s marked order %s as received", actor.capitalize(), updated.id)
        self._notify(updated)
        return OrderResponse(
            message="Order marked as received",
            order=self._to_order_read(updated),
        )

    def _auto_deliver_stale(self) -> None:
        days = get_settings().AUTO_DELIVER_AFTER_DAYS
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        for order in self._orders.list_stale_shipped(cutoff=cutoff):
            try:
                self._deliver_order(order, actor="auto")
            except BadRequestError:
                continue

    def _notify(self, order: Order) -> None:
        notify_order_status(
            user_id=order.user_id,
            order_id=order.id,
            order_number=order.order_number,
            status=order.status,
        )

    def _ensure_status_transition(
        self,
        current: OrderStatus,
        new_status: OrderStatus,
    ) -> None:
        if new_status not in _ADMIN_STATUS_TRANSITIONS[current]:
            raise BadRequestError(
                f"Cannot change order status from {current.value} to {new_status.value}"
            )

    def _get_accessible_order(self, order_id: UUID, *, current_user: User) -> Order:
        order = self._get_order(order_id)
        if current_user.role is not UserRole.ADMIN and order.user_id != current_user.id:
            raise ForbiddenError("You can only access your own orders")
        return order

    def _get_order(self, order_id: UUID) -> Order:
        order = self._orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        return order

    def _to_summary(self, order: Order) -> OrderSummaryRead:
        return OrderSummaryRead(
            id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            customer_name=order.user.name if order.user else None,
            customer_email=order.user.email if order.user else None,
            status=order.status,
            subtotal=order.subtotal,
            stripe_fee=order.stripe_fee,
            total=order.total,
            item_count=len(order.items),
            tracking_number=order.tracking_number,
            shipping_carrier=order.shipping_carrier,
            tracking_url=build_tracking_url(order.shipping_carrier, order.tracking_number),
            amount_refunded=order.amount_refunded or Decimal("0"),
            return_status=_return_status(order),
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    def _to_order_read(self, order: Order) -> OrderRead:
        return OrderRead(
            id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            customer_name=order.user.name if order.user else None,
            customer_email=order.user.email if order.user else None,
            status=order.status,
            subtotal=order.subtotal,
            stripe_fee=order.stripe_fee,
            total=order.total,
            payment_method_id=order.stripe_payment_method_id,
            payment_intent_id=order.stripe_payment_intent_id,
            tracking_number=order.tracking_number,
            shipping_carrier=order.shipping_carrier,
            tracking_url=build_tracking_url(order.shipping_carrier, order.tracking_number),
            shipped_at=order.shipped_at,
            amount_refunded=order.amount_refunded or Decimal("0"),
            stripe_refund_id=order.stripe_refund_id,
            delivered_at=order.delivered_at,
            refunded_at=order.refunded_at,
            return_request=_return_read(order),
            shipping=_shipping_read(order),
            items=[self._to_order_item_read(item) for item in order.items],
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    def _to_order_item_read(self, item: OrderItem) -> OrderItemRead:
        product_name = item.product.name
        if item.variant_name:
            product_name = f"{item.product.name} ({item.variant_name})"
        return OrderItemRead(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=product_name,
            variant_name=item.variant_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
        )


def _shipping_dict(shipping: ShippingAddressRequest) -> dict:
    return {
        "name": shipping.name.strip(),
        "phone": shipping.phone.strip(),
        "address": shipping.address.strip(),
        "city": shipping.city.strip(),
        "country": shipping.country.strip(),
    }


def _return_status(order: Order) -> ReturnStatus | None:
    if not order.return_status:
        return None
    try:
        return ReturnStatus(order.return_status)
    except ValueError:
        return None


def _return_read(order: Order) -> ReturnRequestRead | None:
    status = _return_status(order)
    if status is None:
        return None
    return ReturnRequestRead(
        status=status,
        reason=order.return_reason,
        details=order.return_details,
        admin_note=order.return_admin_note,
    )


def _shipping_read(order: Order) -> ShippingAddressRead | None:
    if not order.shipping_name:
        return None
    return ShippingAddressRead(
        name=order.shipping_name,
        phone=order.shipping_phone or "",
        address=order.shipping_address or "",
        city=order.shipping_city or "",
        country=order.shipping_country or "",
    )
