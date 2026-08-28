from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentAdminDep, CurrentUserDep, ProductServiceDep
from app.api.pagination import PaginationDep
from app.schemas.product import (
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=ProductListResponse,
    response_model_by_alias=True,
    summary="List products with search, pagination, and optional category filter",
)
def list_products(
    _: CurrentUserDep,
    pagination: PaginationDep,
    product_service: ProductServiceDep,
    category_id: UUID | None = Query(
        default=None,
        alias="categoryId",
        description="Optional category filter",
    ),
) -> ProductListResponse:
    return product_service.list_products(pagination, category_id=category_id)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    response_model_by_alias=True,
    summary="Get a product by id",
)
def get_product(
    product_id: UUID,
    _: CurrentUserDep,
    product_service: ProductServiceDep,
) -> ProductResponse:
    return product_service.get_product(product_id)


@router.post(
    "",
    response_model=ProductResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
def create_product(
    payload: ProductCreateRequest,
    _: CurrentAdminDep,
    product_service: ProductServiceDep,
) -> ProductResponse:
    return product_service.create_product(payload)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    response_model_by_alias=True,
    summary="Update a product",
)
def update_product(
    product_id: UUID,
    payload: ProductUpdateRequest,
    _: CurrentAdminDep,
    product_service: ProductServiceDep,
) -> ProductResponse:
    return product_service.update_product(product_id, payload)


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    response_model_by_alias=True,
    summary="Soft delete a product",
)
def delete_product(
    product_id: UUID,
    _: CurrentAdminDep,
    product_service: ProductServiceDep,
) -> ProductResponse:
    return product_service.delete_product(product_id)
