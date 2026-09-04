from decimal import Decimal
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.helpers.stripe_fee import breakdown_with_stripe_fee
from app.models.order import Order, OrderItem, OrderStatus
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
)
from app.schemas.pagination import PaginationQuery, build_pagination_meta
from app.services.stripe_payment_service import StripePaymentService

logger = get_logger(__name__)

_ALLOWED_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.CANCELLED},
    OrderStatus.CANCELLED: set(),
}


class OrderService:
    def __init__(
        self,
        orders: OrderRepository,
        products: ProductRepository,
        variants: ProductVariantRepository,
        stripe_payments: StripePaymentService,
    ) -> None:
        self._orders = orders
        self._products = products
        self._variants = variants
        self._stripe_payments = stripe_payments

    def list_orders(
        self,
        pagination: PaginationQuery,
        *,
        current_user: User,
        status: OrderStatus | None = None,
    ) -> OrderListResponse:
        user_filter = None if current_user.role is UserRole.ADMIN else current_user.id
        items, total = self._orders.list_paginated(
            page=pagination.page,
            limit=pagination.limit,
            user_id=user_filter,
            status=status,
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
        )
        order = self._stripe_payments.charge_order_with_payment_method(
            order,
            payment_method_id=payload.payment_method_id,
            customer_email=current_user.email,
        )
        logger.info("Created order %s for user %s", order.id, current_user.id)

        message = (
            "Order created and paid successfully"
            if order.status is OrderStatus.PAID
            else "Order created successfully"
        )
        return OrderResponse(
            message=message,
            order=self._to_order_read(order),
        )

    def update_order_status(
        self,
        order_id: UUID,
        payload: OrderStatusUpdateRequest,
    ) -> OrderResponse:
        order = self._get_order(order_id)
        self._ensure_status_transition(order.status, payload.status)

        updated = self._orders.update_status(order, status=payload.status)
        logger.info("Updated order %s status to %s", updated.id, updated.status)

        return OrderResponse(
            message="Order status updated successfully",
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
                display_name = f"{product.name} ({variant.name})" if variant.name else product.name
                available = variant.stock
                unit_price = Decimal(variant.price) if variant.price is not None else Decimal(product.price)
            else:
                available = product.stock
                unit_price = Decimal(product.price)

            if available < item.quantity:
                raise BadRequestError(
                    f"Insufficient stock for '{display_name}' "
                    f"(available: {available}, requested: {item.quantity})"
                )

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
                    ok = self._variants.decrement_stock(item["variant_id"], item["quantity"])
                else:
                    ok = self._products.decrement_stock(item["product_id"], item["quantity"])
                if not ok:
                    raise BadRequestError(
                        f"Insufficient stock for '{item['product_name']}' "
                        f"(requested: {item['quantity']})"
                    )
                reserved.append(item)
                if item["variant_id"] is not None:
                    self._sync_product_stock(item["product_id"])
        except Exception:
            for item in reserved:
                if item["variant_id"] is not None:
                    self._variants.increment_stock(item["variant_id"], item["quantity"])
                    self._sync_product_stock(item["product_id"])
                else:
                    self._products.increment_stock(item["product_id"], item["quantity"])
            raise

    def _sync_product_stock(self, product_id: UUID) -> None:
        product = self._products.get_by_id(product_id, include_deleted=True)
        if product is None:
            return
        total = self._variants.sum_stock_by_product(product_id)
        if self._variants.count_by_product(product_id) == 0:
            return
        self._products.update(
            product,
            name=product.name,
            description=product.description,
            brand=product.brand,
            sku=product.sku,
            price=product.price,
            price_sale=product.price_sale,
            colors=list(product.colors or []),
            status=product.status or "",
            stock=total,
            category_id=product.category_id,
        )

    def _ensure_status_transition(
        self,
        current: OrderStatus,
        new_status: OrderStatus,
    ) -> None:
        if new_status not in _ALLOWED_STATUS_TRANSITIONS[current]:
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
            user_id=order.user_id,
            status=order.status,
            subtotal=order.subtotal,
            stripe_fee=order.stripe_fee,
            total=order.total,
            item_count=len(order.items),
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    def _to_order_read(self, order: Order) -> OrderRead:
        return OrderRead(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            subtotal=order.subtotal,
            stripe_fee=order.stripe_fee,
            total=order.total,
            payment_method_id=order.stripe_payment_method_id,
            payment_intent_id=order.stripe_payment_intent_id,
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
