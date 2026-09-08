from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CategoryServiceDep, CurrentCatalogStaffDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.category import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateRequest,
)

router = APIRouter(prefix="/categories", tags=["Admin — Categories"])


@router.get(
    "",
    response_model=CategoryListResponse,
    response_model_by_alias=True,
    summary="List categories (admin)",
)
def list_categories(
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
    is_active: bool | None = Query(default=None, alias="isActive"),
    _: CurrentCatalogStaffDep = None,
    category_service: CategoryServiceDep = None,
) -> CategoryListResponse:
    return category_service.list_categories(
        build_pagination(page, limit, search),
        is_active=is_active,
    )


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    response_model_by_alias=True,
    summary="Get a category by id (admin)",
)
def get_category(
    category_id: UUID,
    _: CurrentCatalogStaffDep,
    category_service: CategoryServiceDep,
) -> CategoryResponse:
    return category_service.get_category(category_id)


@router.post(
    "",
    response_model=CategoryResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
def create_category(
    payload: CategoryCreateRequest,
    _: CurrentCatalogStaffDep,
    category_service: CategoryServiceDep,
) -> CategoryResponse:
    return category_service.create_category(payload)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    response_model_by_alias=True,
    summary="Update a category",
)
def update_category(
    category_id: UUID,
    payload: CategoryUpdateRequest,
    _: CurrentCatalogStaffDep,
    category_service: CategoryServiceDep,
) -> CategoryResponse:
    return category_service.update_category(category_id, payload)


@router.delete(
    "/{category_id}",
    response_model=CategoryResponse,
    response_model_by_alias=True,
    summary="Soft delete a category",
)
def delete_category(
    category_id: UUID,
    _: CurrentCatalogStaffDep,
    category_service: CategoryServiceDep,
) -> CategoryResponse:
    return category_service.delete_category(category_id)
