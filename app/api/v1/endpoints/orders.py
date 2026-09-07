from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, OrderServiceDep, StripePaymentServiceDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.models.order import OrderStatus
from app.schemas.order import OrderCreateRequest, OrderListResponse, OrderResponse
from app.schemas.payment import CheckoutSessionResponse, PayOrderRequest

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "",
    response_model=OrderListResponse,
    response_model_by_alias=True,
    summary="List the current user's orders",
)
def list_orders(
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
    current_user: CurrentUserDep = None,
    order_service: OrderServiceDep = None,
    order_status: OrderStatus | None = Query(
        default=None,
        alias="status",
        description="Optional status filter",
    ),
) -> OrderListResponse:
    return order_service.list_orders(
        build_pagination(page, limit, search),
        current_user=current_user,
        status=order_status,
        all_users=False,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    response_model_by_alias=True,
    summary="Get one of the current user's orders",
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


@router.post(
    "/{order_id}/pay",
    response_model=OrderResponse,
    response_model_by_alias=True,
    summary="Pay a pending order with a Stripe payment method id",
)
def pay_order(
    order_id: UUID,
    payload: PayOrderRequest,
    current_user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> OrderResponse:
    return order_service.pay_order(
        order_id,
        payment_method_id=payload.payment_method_id,
        current_user=current_user,
    )
