from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentAdminDep, CurrentUserDep, ProductServiceDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.product import (
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductSort,
    ProductStatus,
    ProductUpdateRequest,
    ProductVariantCreateRequest,
    ProductVariantResponse,
    ProductVariantUpdateRequest,
    RelatedProductsResponse,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=ProductListResponse,
    response_model_by_alias=True,
    summary="List products with search, filters, sort, and pagination",
)
def list_products(
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
    _: CurrentUserDep = None,
    product_service: ProductServiceDep = None,
    category_id: UUID | None = Query(
        default=None,
        alias="categoryId",
        description="Optional category filter",
    ),
    status_filter: ProductStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by status: new or sale",
    ),
    colors: list[str] | None = Query(
        default=None,
        description="Filter by one or more colors",
    ),
    min_price: Decimal | None = Query(default=None, alias="minPrice", ge=0),
    max_price: Decimal | None = Query(default=None, alias="maxPrice", ge=0),
    on_sale: bool | None = Query(
        default=None,
        alias="onSale",
        description="When true, only products with status=sale or a sale price",
    ),
    sort: ProductSort | None = Query(
        default=None,
        description="newest | priceAsc | priceDesc | nameAsc",
    ),
) -> ProductListResponse:
    return product_service.list_products(
        build_pagination(page, limit, search),
        category_id=category_id,
        status=status_filter,
        colors=colors,
        min_price=min_price,
        max_price=max_price,
        on_sale=on_sale,
        sort=sort,
    )


@router.get(
    "/related/{product_id}",
    response_model=RelatedProductsResponse,
    response_model_by_alias=True,
    summary="Get related products in the same category",
)
def get_related_products(
    product_id: UUID,
    _: CurrentUserDep,
    product_service: ProductServiceDep,
    limit: int = Query(default=8, ge=1, le=16),
) -> RelatedProductsResponse:
    return product_service.get_related_products(product_id, limit=limit)


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
    summary="Update a product (optionally replace variants)",
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


@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product variant",
)
def create_variant(
    product_id: UUID,
    payload: ProductVariantCreateRequest,
    _: CurrentAdminDep,
    product_service: ProductServiceDep,
) -> ProductVariantResponse:
    return product_service.create_variant(product_id, payload)


@router.put(
    "/{product_id}/variants/{variant_id}",
    response_model=ProductVariantResponse,
    response_model_by_alias=True,
    summary="Update a product variant",
)
def update_variant(
    product_id: UUID,
    variant_id: UUID,
    payload: ProductVariantUpdateRequest,
    _: CurrentAdminDep,
    product_service: ProductServiceDep,
) -> ProductVariantResponse:
    return product_service.update_variant(product_id, variant_id, payload)


@router.delete(
    "/{product_id}/variants/{variant_id}",
    response_model=ProductVariantResponse,
    response_model_by_alias=True,
    summary="Delete a product variant",
)
def delete_variant(
    product_id: UUID,
    variant_id: UUID,
    _: CurrentAdminDep,
    product_service: ProductServiceDep,
) -> ProductVariantResponse:
    return product_service.delete_variant(product_id, variant_id)
