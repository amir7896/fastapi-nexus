from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import BrandServiceDep, CurrentAdminDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.brand import BrandCreateRequest, BrandListResponse, BrandResponse, BrandUpdateRequest

router = APIRouter(prefix="/brands", tags=["Admin — Brands"])


@router.get(
    "",
    response_model=BrandListResponse,
    response_model_by_alias=True,
    summary="List brands (admin)",
)
def list_brands(
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
    is_active: bool | None = Query(default=None, alias="isActive"),
    _: CurrentAdminDep = None,
    brand_service: BrandServiceDep = None,
) -> BrandListResponse:
    return brand_service.list_brands(build_pagination(page, limit, search), is_active=is_active)


@router.get(
    "/{brand_id}",
    response_model=BrandResponse,
    response_model_by_alias=True,
    summary="Get a brand by id (admin)",
)
def get_brand(
    brand_id: UUID,
    _: CurrentAdminDep,
    brand_service: BrandServiceDep,
) -> BrandResponse:
    return brand_service.get_brand(brand_id)


@router.post(
    "",
    response_model=BrandResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Create a brand",
)
def create_brand(
    payload: BrandCreateRequest,
    _: CurrentAdminDep,
    brand_service: BrandServiceDep,
) -> BrandResponse:
    return brand_service.create_brand(payload)


@router.put(
    "/{brand_id}",
    response_model=BrandResponse,
    response_model_by_alias=True,
    summary="Update a brand",
)
def update_brand(
    brand_id: UUID,
    payload: BrandUpdateRequest,
    _: CurrentAdminDep,
    brand_service: BrandServiceDep,
) -> BrandResponse:
    return brand_service.update_brand(brand_id, payload)


@router.delete(
    "/{brand_id}",
    response_model=BrandResponse,
    response_model_by_alias=True,
    summary="Soft delete a brand",
)
def delete_brand(
    brand_id: UUID,
    _: CurrentAdminDep,
    brand_service: BrandServiceDep,
) -> BrandResponse:
    return brand_service.delete_brand(brand_id)
