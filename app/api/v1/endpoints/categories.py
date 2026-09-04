from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CategoryServiceDep, CurrentAdminDep, CurrentUserDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.category import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateRequest,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=CategoryListResponse,
    response_model_by_alias=True,
    summary="List categories with search and pagination",
)
def list_categories(
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
    _: CurrentUserDep = None,
    category_service: CategoryServiceDep = None,
) -> CategoryListResponse:
    return category_service.list_categories(build_pagination(page, limit, search))


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    response_model_by_alias=True,
    summary="Get a category by id",
)
def get_category(
    category_id: UUID,
    _: CurrentUserDep,
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
    _: CurrentAdminDep,
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
    _: CurrentAdminDep,
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
    _: CurrentAdminDep,
    category_service: CategoryServiceDep,
) -> CategoryResponse:
    return category_service.delete_category(category_id)
