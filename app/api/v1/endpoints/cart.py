from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CartServiceDep, CurrentUserDep
from app.schemas.cart import (
    CartCheckoutRequest,
    CartCheckoutResponse,
    CartItemAddRequest,
    CartItemUpdateRequest,
    CartResponse,
)

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get(
    "",
    response_model=CartResponse,
    response_model_by_alias=True,
    summary="Get the current user's cart",
)
def get_cart(
    current_user: CurrentUserDep,
    cart_service: CartServiceDep,
) -> CartResponse:
    return cart_service.get_cart(current_user)


@router.post(
    "/items",
    response_model=CartResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Add a product (optional variant) to the cart",
)
def add_cart_item(
    payload: CartItemAddRequest,
    current_user: CurrentUserDep,
    cart_service: CartServiceDep,
) -> CartResponse:
    return cart_service.add_item(payload, current_user=current_user)


@router.put(
    "/items/{product_id}",
    response_model=CartResponse,
    response_model_by_alias=True,
    summary="Update quantity for a cart item",
)
def update_cart_item(
    product_id: UUID,
    payload: CartItemUpdateRequest,
    current_user: CurrentUserDep,
    cart_service: CartServiceDep,
    variant_id: UUID | None = Query(default=None, alias="variantId"),
) -> CartResponse:
    if payload.variant_id is None and variant_id is not None:
        payload = payload.model_copy(update={"variant_id": variant_id})
    return cart_service.update_item(product_id, payload, current_user=current_user)


@router.delete(
    "/items/{product_id}",
    response_model=CartResponse,
    response_model_by_alias=True,
    summary="Remove a product/variant from the cart",
)
def remove_cart_item(
    product_id: UUID,
    current_user: CurrentUserDep,
    cart_service: CartServiceDep,
    variant_id: UUID | None = Query(default=None, alias="variantId"),
) -> CartResponse:
    return cart_service.remove_item(
        product_id,
        current_user=current_user,
        variant_id=variant_id,
    )


@router.delete(
    "",
    response_model=CartResponse,
    response_model_by_alias=True,
    summary="Clear the cart",
)
def clear_cart(
    current_user: CurrentUserDep,
    cart_service: CartServiceDep,
) -> CartResponse:
    return cart_service.clear_cart(current_user)


@router.post(
    "/checkout",
    response_model=CartCheckoutResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order from cart items and clear the cart",
)
def checkout_cart(
    payload: CartCheckoutRequest,
    current_user: CurrentUserDep,
    cart_service: CartServiceDep,
) -> CartCheckoutResponse:
    return cart_service.checkout(payload, current_user=current_user)
