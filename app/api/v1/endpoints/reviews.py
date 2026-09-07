from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, OptionalUserDep, ReviewServiceDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.review import (
    OrderReviewTargetsResponse,
    ReviewCreateRequest,
    ReviewEligibilityResponse,
    ReviewListResponse,
    ReviewResponse,
)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get(
    "/products/{product_id}",
    response_model=ReviewListResponse,
    response_model_by_alias=True,
    summary="List reviews for a product",
)
def list_product_reviews(
    product_id: UUID,
    review_service: ReviewServiceDep,
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
) -> ReviewListResponse:
    return review_service.list_product_reviews(product_id, build_pagination(page, limit, search))


@router.get(
    "/products/{product_id}/eligibility",
    response_model=ReviewEligibilityResponse,
    response_model_by_alias=True,
    summary="Whether the current user can review this product",
)
def get_review_eligibility(
    product_id: UUID,
    review_service: ReviewServiceDep,
    current_user: OptionalUserDep,
) -> ReviewEligibilityResponse:
    return review_service.get_eligibility(product_id, current_user=current_user)


@router.post(
    "/products/{product_id}",
    response_model=ReviewResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Create or update a review after delivery",
)
def upsert_review(
    product_id: UUID,
    payload: ReviewCreateRequest,
    current_user: CurrentUserDep,
    review_service: ReviewServiceDep,
) -> ReviewResponse:
    return review_service.upsert_review(product_id, payload, current_user=current_user)


@router.get(
    "/orders/{order_id}/targets",
    response_model=OrderReviewTargetsResponse,
    response_model_by_alias=True,
    summary="Products on a delivered order that can be reviewed",
)
def list_order_review_targets(
    order_id: UUID,
    current_user: CurrentUserDep,
    review_service: ReviewServiceDep,
) -> OrderReviewTargetsResponse:
    return review_service.list_order_targets(order_id, current_user=current_user)


@router.delete(
    "/{review_id}",
    response_model=ReviewResponse,
    response_model_by_alias=True,
    summary="Delete a review you wrote",
)
def delete_review(
    review_id: UUID,
    current_user: CurrentUserDep,
    review_service: ReviewServiceDep,
) -> ReviewResponse:
    return review_service.delete_review(review_id, current_user=current_user)
