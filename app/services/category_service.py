from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategoryRead,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.schemas.pagination import PaginationQuery, build_pagination_meta

logger = get_logger(__name__)


class CategoryService:
    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    def list_categories(
        self,
        pagination: PaginationQuery,
        *,
        is_active: bool | None = None,
    ) -> CategoryListResponse:
        items, total = self._categories.list_active_paginated(
            page=pagination.page,
            limit=pagination.limit,
            search=pagination.search,
            is_active=is_active,
        )
        return CategoryListResponse(
            message="Categories fetched successfully",
            data=[CategoryRead.model_validate(item) for item in items],
            meta=build_pagination_meta(
                total=total,
                page=pagination.page,
                limit=pagination.limit,
            ),
        )

    def get_category(self, category_id: UUID, *, require_active: bool = False) -> CategoryResponse:
        category = self._get_active_category(category_id)
        if require_active and not category.is_active:
            raise NotFoundError("Category not found")
        return CategoryResponse(
            message="Category fetched successfully",
            category=CategoryRead.model_validate(category),
        )

    def create_category(self, payload: CategoryCreateRequest) -> CategoryResponse:
        if self._categories.name_exists(payload.name):
            raise ConflictError("Category name already exists")

        category = self._categories.create(name=payload.name, is_active=payload.is_active)
        logger.info("Created category %s", category.id)

        return CategoryResponse(
            message="Category created successfully",
            category=CategoryRead.model_validate(category),
        )

    def update_category(
        self,
        category_id: UUID,
        payload: CategoryUpdateRequest,
    ) -> CategoryResponse:
        category = self._get_active_category(category_id)

        if payload.name is not None and self._categories.name_exists(payload.name, exclude_id=category.id):
            raise ConflictError("Category name already exists")

        updated = self._categories.update(category, name=payload.name, is_active=payload.is_active)
        logger.info("Updated category %s", updated.id)

        return CategoryResponse(
            message="Category updated successfully",
            category=CategoryRead.model_validate(updated),
        )

    def delete_category(self, category_id: UUID) -> CategoryResponse:
        category = self._get_active_category(category_id)
        deleted = self._categories.soft_delete(category)
        logger.info("Soft deleted category %s", deleted.id)

        return CategoryResponse(
            message="Category deleted successfully",
            category=CategoryRead.model_validate(deleted),
        )

    def _get_active_category(self, category_id: UUID):
        category = self._categories.get_by_id(category_id)
        if category is None:
            raise NotFoundError("Category not found")
        return category
