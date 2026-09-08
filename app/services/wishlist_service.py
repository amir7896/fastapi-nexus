from uuid import UUID

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.repositories.product_repository import ProductRepository
from app.repositories.wishlist_repository import WishlistRepository
from app.schemas.wishlist import (
    WishlistAddRequest,
    WishlistIdsResponse,
    WishlistItemResponse,
    WishlistListResponse,
)
from app.services.product_service import ProductService


class WishlistService:
    def __init__(
        self,
        wishlist: WishlistRepository,
        products: ProductRepository,
        product_service: ProductService,
    ) -> None:
        self._wishlist = wishlist
        self._products = products
        self._product_service = product_service

    def list_ids(self, current_user: User) -> WishlistIdsResponse:
        return WishlistIdsResponse(
            message="Wishlist ids fetched",
            ids=self._wishlist.list_ids(current_user.id),
        )

    def list_items(self, current_user: User) -> WishlistListResponse:
        items = self._wishlist.list_items(current_user.id)
        products = [self._to_product(item) for item in items if item.product is not None]
        return WishlistListResponse(
            message="Wishlist fetched successfully",
            data=products,
            ids=[product.id for product in products],
        )

    def add_item(self, payload: WishlistAddRequest, *, current_user: User) -> WishlistItemResponse:
        product = self._products.get_by_id(payload.product_id)
        if product is None:
            raise NotFoundError("Product not found")
        self._wishlist.add(user_id=current_user.id, product_id=product.id)
        return WishlistItemResponse(
            message="Saved to wishlist",
            product=self._product_service._to_product_read(product),
            ids=self._wishlist.list_ids(current_user.id),
        )

    def remove_item(self, product_id: UUID, *, current_user: User) -> WishlistIdsResponse:
        item = self._wishlist.get_item(current_user.id, product_id)
        if item is None:
            raise NotFoundError("Wishlist item not found")
        self._wishlist.remove(item)
        return WishlistIdsResponse(
            message="Removed from wishlist",
            ids=self._wishlist.list_ids(current_user.id),
        )

    def _to_product(self, item: WishlistItem):
        return self._product_service._to_product_read(item.product)
