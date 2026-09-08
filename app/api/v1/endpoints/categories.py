from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CatalogViewerDep, CategoryServiceDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.category import CategoryListResponse, CategoryResponse

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
    _: CatalogViewerDep = None,
    category_service: CategoryServiceDep = None,
) -> CategoryListResponse:
    return category_service.list_categories(build_pagination(page, limit, search), is_active=True)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    response_model_by_alias=True,
    summary="Get a category by id",
)
def get_category(
    category_id: UUID,
    _: CatalogViewerDep,
    category_service: CategoryServiceDep,
) -> CategoryResponse:
    return category_service.get_category(category_id, require_active=True)
