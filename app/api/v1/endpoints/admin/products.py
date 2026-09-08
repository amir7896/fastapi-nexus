from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile, status

from app.api.deps import AuditServiceDep, CurrentCatalogStaffDep, ProductServiceDep
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
)

router = APIRouter(prefix="/products", tags=["Admin — Products"])


@router.get(
    "",
    response_model=ProductListResponse,
    response_model_by_alias=True,
    summary="List products (admin)",
)
def list_products(
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
    _: CurrentCatalogStaffDep = None,
    product_service: ProductServiceDep = None,
    category_id: list[UUID] | None = Query(default=None, alias="categoryId"),
    brand_id: UUID | None = Query(default=None, alias="brandId"),
    status_filter: list[ProductStatus] | None = Query(default=None, alias="status"),
    colors: list[str] | None = Query(default=None),
    min_price: Decimal | None = Query(default=None, alias="minPrice", ge=0),
    max_price: Decimal | None = Query(default=None, alias="maxPrice", ge=0),
    on_sale: bool | None = Query(default=None, alias="onSale"),
    sort: ProductSort | None = Query(default=None),
) -> ProductListResponse:
    return product_service.list_products(
        build_pagination(page, limit, search),
        category_ids=category_id,
        brand_id=brand_id,
        statuses=status_filter,
        colors=colors,
        min_price=min_price,
        max_price=max_price,
        on_sale=on_sale,
        sort=sort,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    response_model_by_alias=True,
    summary="Get a product by id (admin)",
)
def get_product(
    product_id: UUID,
    _: CurrentCatalogStaffDep,
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
    current_admin: CurrentCatalogStaffDep,
    product_service: ProductServiceDep,
    audit: AuditServiceDep,
) -> ProductResponse:
    result = product_service.create_product(payload)
    audit.record(
        actor=current_admin,
        action="catalog.product_created",
        target_type="product",
        target_id=result.product.id,
        summary=f"Created product {result.product.name}",
    )
    return result


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    response_model_by_alias=True,
    summary="Update a product (optionally replace variants)",
)
def update_product(
    product_id: UUID,
    payload: ProductUpdateRequest,
    current_admin: CurrentCatalogStaffDep,
    product_service: ProductServiceDep,
    audit: AuditServiceDep,
) -> ProductResponse:
    result = product_service.update_product(product_id, payload)
    audit.record(
        actor=current_admin,
        action="catalog.product_updated",
        target_type="product",
        target_id=result.product.id,
        summary=f"Updated product {result.product.name}",
    )
    return result


@router.post(
    "/{product_id}/image",
    response_model=ProductResponse,
    response_model_by_alias=True,
    summary="Upload a product image",
)
def upload_product_image(
    product_id: UUID,
    _: CurrentCatalogStaffDep,
    product_service: ProductServiceDep,
    file: UploadFile = File(...),
) -> ProductResponse:
    return product_service.upload_product_image(product_id, file)


@router.delete(
    "/{product_id}/image",
    response_model=ProductResponse,
    response_model_by_alias=True,
    summary="Remove a product image",
)
def delete_product_image(
    product_id: UUID,
    _: CurrentCatalogStaffDep,
    product_service: ProductServiceDep,
) -> ProductResponse:
    return product_service.delete_product_image(product_id)


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    response_model_by_alias=True,
    summary="Soft delete a product",
)
def delete_product(
    product_id: UUID,
    current_admin: CurrentCatalogStaffDep,
    product_service: ProductServiceDep,
    audit: AuditServiceDep,
) -> ProductResponse:
    result = product_service.delete_product(product_id)
    audit.record(
        actor=current_admin,
        action="catalog.product_deleted",
        target_type="product",
        target_id=result.product.id,
        summary=f"Deleted product {result.product.name}",
    )
    return result


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
    _: CurrentCatalogStaffDep,
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
    _: CurrentCatalogStaffDep,
    product_service: ProductServiceDep,
) -> ProductVariantResponse:
    return product_service.update_variant(product_id, variant_id, payload)


@router.post(
    "/{product_id}/variants/{variant_id}/image",
    response_model=ProductVariantResponse,
    response_model_by_alias=True,
    summary="Upload a variant image",
)
def upload_variant_image(
    product_id: UUID,
    variant_id: UUID,
    _: CurrentCatalogStaffDep,
    product_service: ProductServiceDep,
    file: UploadFile = File(...),
) -> ProductVariantResponse:
    return product_service.upload_variant_image(product_id, variant_id, file)


@router.delete(
    "/{product_id}/variants/{variant_id}/image",
    response_model=ProductVariantResponse,
    response_model_by_alias=True,
    summary="Remove a variant image",
)
def delete_variant_image(
    product_id: UUID,
    variant_id: UUID,
    _: CurrentCatalogStaffDep,
    product_service: ProductServiceDep,
) -> ProductVariantResponse:
    return product_service.delete_variant_image(product_id, variant_id)


@router.delete(
    "/{product_id}/variants/{variant_id}",
    response_model=ProductVariantResponse,
    response_model_by_alias=True,
    summary="Delete a product variant",
)
def delete_variant(
    product_id: UUID,
    variant_id: UUID,
    _: CurrentCatalogStaffDep,
    product_service: ProductServiceDep,
) -> ProductVariantResponse:
    return product_service.delete_variant(product_id, variant_id)
