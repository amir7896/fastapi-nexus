from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.repositories.brand_repository import BrandRepository
from app.schemas.brand import (
    BrandCreateRequest,
    BrandListResponse,
    BrandRead,
    BrandResponse,
    BrandUpdateRequest,
)
from app.schemas.pagination import PaginationQuery, build_pagination_meta

logger = get_logger(__name__)


class BrandService:
    def __init__(self, brands: BrandRepository) -> None:
        self._brands = brands

    def list_brands(
        self,
        pagination: PaginationQuery,
        *,
        is_active: bool | None = None,
    ) -> BrandListResponse:
        items, total = self._brands.list_active_paginated(
            page=pagination.page,
            limit=pagination.limit,
            search=pagination.search,
            is_active=is_active,
        )
        return BrandListResponse(
            message="Brands fetched successfully",
            data=[BrandRead.model_validate(item) for item in items],
            meta=build_pagination_meta(total=total, page=pagination.page, limit=pagination.limit),
        )

    def get_brand(self, brand_id: UUID, *, require_active: bool = False) -> BrandResponse:
        brand = self._get_active_brand(brand_id)
        if require_active and not brand.is_active:
            raise NotFoundError("Brand not found")
        return BrandResponse(
            message="Brand fetched successfully",
            brand=BrandRead.model_validate(brand),
        )

    def create_brand(self, payload: BrandCreateRequest) -> BrandResponse:
        if self._brands.name_exists(payload.name):
            raise ConflictError("Brand name already exists")
        brand = self._brands.create(name=payload.name, is_active=payload.is_active)
        logger.info("Created brand %s", brand.id)
        return BrandResponse(
            message="Brand created successfully",
            brand=BrandRead.model_validate(brand),
        )

    def update_brand(self, brand_id: UUID, payload: BrandUpdateRequest) -> BrandResponse:
        brand = self._get_active_brand(brand_id)
        if payload.name is not None and self._brands.name_exists(payload.name, exclude_id=brand.id):
            raise ConflictError("Brand name already exists")
        updated = self._brands.update(brand, name=payload.name, is_active=payload.is_active)
        logger.info("Updated brand %s", updated.id)
        return BrandResponse(
            message="Brand updated successfully",
            brand=BrandRead.model_validate(updated),
        )

    def delete_brand(self, brand_id: UUID) -> BrandResponse:
        brand = self._get_active_brand(brand_id)
        deleted = self._brands.soft_delete(brand)
        logger.info("Soft deleted brand %s", deleted.id)
        return BrandResponse(
            message="Brand deleted successfully",
            brand=BrandRead.model_validate(deleted),
        )

    def _get_active_brand(self, brand_id: UUID):
        brand = self._brands.get_by_id(brand_id)
        if brand is None:
            raise NotFoundError("Brand not found")
        return brand
