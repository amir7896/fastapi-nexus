from uuid import UUID

from fastapi import APIRouter

from app.api.deps import BrandServiceDep, CurrentUserDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.brand import BrandListResponse, BrandResponse

router = APIRouter(prefix="/brands", tags=["Brands"])


@router.get(
    "",
    response_model=BrandListResponse,
    response_model_by_alias=True,
    summary="List brands with search and pagination",
)
def list_brands(
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
    _: CurrentUserDep = None,
    brand_service: BrandServiceDep = None,
) -> BrandListResponse:
    return brand_service.list_brands(build_pagination(page, limit, search), is_active=True)


@router.get(
    "/{brand_id}",
    response_model=BrandResponse,
    response_model_by_alias=True,
    summary="Get a brand by id",
)
def get_brand(
    brand_id: UUID,
    _: CurrentUserDep,
    brand_service: BrandServiceDep,
) -> BrandResponse:
    return brand_service.get_brand(brand_id, require_active=True)
