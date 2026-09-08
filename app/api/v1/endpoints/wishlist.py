from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, WishlistServiceDep
from app.schemas.wishlist import (
    WishlistAddRequest,
    WishlistIdsResponse,
    WishlistItemResponse,
    WishlistListResponse,
)

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get(
    "",
    response_model=WishlistListResponse,
    response_model_by_alias=True,
    summary="List products saved to the wishlist",
)
def list_wishlist(
    current_user: CurrentUserDep,
    wishlist_service: WishlistServiceDep,
) -> WishlistListResponse:
    return wishlist_service.list_items(current_user)


@router.get(
    "/ids",
    response_model=WishlistIdsResponse,
    response_model_by_alias=True,
    summary="List wishlist product ids",
)
def list_wishlist_ids(
    current_user: CurrentUserDep,
    wishlist_service: WishlistServiceDep,
) -> WishlistIdsResponse:
    return wishlist_service.list_ids(current_user)


@router.post(
    "",
    response_model=WishlistItemResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Save a product to the wishlist",
)
def add_wishlist_item(
    payload: WishlistAddRequest,
    current_user: CurrentUserDep,
    wishlist_service: WishlistServiceDep,
) -> WishlistItemResponse:
    return wishlist_service.add_item(payload, current_user=current_user)


@router.delete(
    "/{product_id}",
    response_model=WishlistIdsResponse,
    response_model_by_alias=True,
    summary="Remove a product from the wishlist",
)
def remove_wishlist_item(
    product_id: UUID,
    current_user: CurrentUserDep,
    wishlist_service: WishlistServiceDep,
) -> WishlistIdsResponse:
    return wishlist_service.remove_item(product_id, current_user=current_user)
