from uuid import UUID

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.pagination import PaginationQuery, build_pagination_meta
from app.schemas.product import (
    ProductCreateRequest,
    ProductListResponse,
    ProductRead,
    ProductResponse,
    ProductUpdateRequest,
)

logger = get_logger(__name__)


class ProductService:
    def __init__(
        self,
        products: ProductRepository,
        categories: CategoryRepository,
    ) -> None:
        self._products = products
        self._categories = categories

    def list_products(
        self,
        pagination: PaginationQuery,
        *,
        category_id: UUID | None = None,
    ) -> ProductListResponse:
        items, total = self._products.list_active_paginated(
            page=pagination.page,
            limit=pagination.limit,
            search=pagination.search,
            category_id=category_id,
        )
        return ProductListResponse(
            message="Products fetched successfully",
            data=[ProductRead.model_validate(item) for item in items],
            meta=build_pagination_meta(
                total=total,
                page=pagination.page,
                limit=pagination.limit,
            ),
        )

    def get_product(self, product_id: UUID) -> ProductResponse:
        product = self._get_active_product(product_id)
        return ProductResponse(
            message="Product fetched successfully",
            product=ProductRead.model_validate(product),
        )

    def create_product(self, payload: ProductCreateRequest) -> ProductResponse:
        self._ensure_category_exists(payload.category_id)

        product = self._products.create(
            name=payload.name,
            description=payload.description,
            price=payload.price,
            category_id=payload.category_id,
        )
        logger.info("Created product %s", product.id)

        return ProductResponse(
            message="Product created successfully",
            product=ProductRead.model_validate(product),
        )

    def update_product(
        self,
        product_id: UUID,
        payload: ProductUpdateRequest,
    ) -> ProductResponse:
        product = self._get_active_product(product_id)
        self._ensure_category_exists(payload.category_id)

        updated = self._products.update(
            product,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            category_id=payload.category_id,
        )
        logger.info("Updated product %s", updated.id)

        return ProductResponse(
            message="Product updated successfully",
            product=ProductRead.model_validate(updated),
        )

    def delete_product(self, product_id: UUID) -> ProductResponse:
        product = self._get_active_product(product_id)
        deleted = self._products.soft_delete(product)
        logger.info("Soft deleted product %s", deleted.id)

        return ProductResponse(
            message="Product deleted successfully",
            product=ProductRead.model_validate(deleted),
        )

    def _get_active_product(self, product_id: UUID):
        product = self._products.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return product

    def _ensure_category_exists(self, category_id: UUID) -> None:
        if self._categories.get_by_id(category_id) is None:
            raise NotFoundError("Category not found")
