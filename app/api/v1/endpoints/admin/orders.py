from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentAdminDep, OrderServiceDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.models.order import OrderStatus
from app.schemas.order import (
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
    ReturnReviewRequest,
)

router = APIRouter(prefix="/orders", tags=["Admin — Orders"])


@router.get(
    "",
    response_model=OrderListResponse,
    response_model_by_alias=True,
    summary="List all orders",
)
def list_orders(
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
    current_admin: CurrentAdminDep = None,
    order_service: OrderServiceDep = None,
    order_status: OrderStatus | None = Query(
        default=None,
        alias="status",
        description="Optional status filter",
    ),
) -> OrderListResponse:
    return order_service.list_orders(
        build_pagination(page, limit, search),
        current_user=current_admin,
        status=order_status,
        all_users=True,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    response_model_by_alias=True,
    summary="Get any order by id",
)
def get_order(
    order_id: UUID,
    current_admin: CurrentAdminDep,
    order_service: OrderServiceDep,
) -> OrderResponse:
    return order_service.get_order(order_id, current_user=current_admin)


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    response_model_by_alias=True,
    summary="Update order status",
)
def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdateRequest,
    _: CurrentAdminDep,
    order_service: OrderServiceDep,
) -> OrderResponse:
    return order_service.update_order_status(order_id, payload)


@router.post(
    "/{order_id}/return/review",
    response_model=OrderResponse,
    response_model_by_alias=True,
    summary="Approve or reject a customer return request",
)
def review_return(
    order_id: UUID,
    payload: ReturnReviewRequest,
    _: CurrentAdminDep,
    order_service: OrderServiceDep,
) -> OrderResponse:
    return order_service.review_return(order_id, payload)
