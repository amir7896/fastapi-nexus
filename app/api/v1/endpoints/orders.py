from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentAdminDep, CurrentUserDep, OrderServiceDep, StripePaymentServiceDep
from app.api.pagination import PaginationDep
from app.models.order import OrderStatus
from app.schemas.order import (
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
)
from app.schemas.payment import CheckoutSessionResponse

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "",
    response_model=OrderListResponse,
    response_model_by_alias=True,
    summary="List orders with pagination (own orders, or all if admin)",
)
def list_orders(
    current_user: CurrentUserDep,
    pagination: PaginationDep,
    order_service: OrderServiceDep,
    order_status: OrderStatus | None = Query(
        default=None,
        alias="status",
        description="Optional status filter",
    ),
) -> OrderListResponse:
    return order_service.list_orders(
        pagination,
        current_user=current_user,
        status=order_status,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    response_model_by_alias=True,
    summary="Get an order by id",
)
def get_order(
    order_id: UUID,
    current_user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> OrderResponse:
    return order_service.get_order(order_id, current_user=current_user)


@router.post(
    "",
    response_model=OrderResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order from product items",
)
def create_order(
    payload: OrderCreateRequest,
    current_user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> OrderResponse:
    return order_service.create_order(payload, current_user=current_user)


@router.post(
    "/{order_id}/checkout",
    response_model=CheckoutSessionResponse,
    response_model_by_alias=True,
    summary="Create a Stripe checkout session for a pending order",
)
def create_order_checkout(
    order_id: UUID,
    current_user: CurrentUserDep,
    stripe_payment_service: StripePaymentServiceDep,
) -> CheckoutSessionResponse:
    return stripe_payment_service.create_checkout_session(
        order_id,
        current_user=current_user,
    )


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    response_model_by_alias=True,
    summary="Update order status (admin only)",
)
def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdateRequest,
    _: CurrentAdminDep,
    order_service: OrderServiceDep,
) -> OrderResponse:
    return order_service.update_order_status(order_id, payload)
