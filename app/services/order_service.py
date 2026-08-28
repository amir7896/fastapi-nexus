from decimal import Decimal
from uuid import UUID

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User, UserRole
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
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
        stripe_payments: StripePaymentService,
    ) -> None:
        self._orders = orders
        self._products = products
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
        order = self._orders.create(user_id=current_user.id, line_items=line_items)
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
        seen_product_ids: set[UUID] = set()
        line_items: list[dict] = []

        for item in payload.items:
            if item.product_id in seen_product_ids:
                raise BadRequestError("Duplicate product in order items")
            seen_product_ids.add(item.product_id)

            product = self._products.get_by_id(item.product_id)
            if product is None:
                raise NotFoundError(f"Product not found: {item.product_id}")

            unit_price = Decimal(product.price)
            subtotal = unit_price * item.quantity
            line_items.append(
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                }
            )

        return line_items

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
            total=order.total,
            payment_method_id=order.stripe_payment_method_id,
            payment_intent_id=order.stripe_payment_intent_id,
            items=[self._to_order_item_read(item) for item in order.items],
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    def _to_order_item_read(self, item: OrderItem) -> OrderItemRead:
        return OrderItemRead(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
        )
