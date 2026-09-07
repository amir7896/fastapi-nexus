from decimal import Decimal
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.logging import get_logger
from app.models.product import Product
from app.models.product_variant import ProductVariant
from fastapi import UploadFile

from app.repositories.brand_repository import BrandRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.product_variant_repository import ProductVariantRepository
from app.services.image_storage_service import ImageStorageService
from app.schemas.pagination import PaginationQuery, build_pagination_meta
from app.schemas.dashboard import LowStockItemRead, LowStockListResponse
from app.schemas.product import (
    ProductCreateRequest,
    ProductListResponse,
    ProductRead,
    ProductResponse,
    ProductUpdateRequest,
    ProductVariantCreateRequest,
    ProductVariantRead,
    ProductVariantResponse,
    ProductVariantUpdateRequest,
    ProductVariantUpsertRequest,
    RelatedProductsResponse,
)

logger = get_logger(__name__)


class ProductService:
    def __init__(
        self,
        products: ProductRepository,
        categories: CategoryRepository,
        brands: BrandRepository,
        variants: ProductVariantRepository,
        images: ImageStorageService,
    ) -> None:
        self._products = products
        self._categories = categories
        self._brands = brands
        self._variants = variants
        self._images = images

    def list_products(
        self,
        pagination: PaginationQuery,
        *,
        category_ids: list[UUID] | None = None,
        brand_id: UUID | None = None,
        statuses: list[str] | None = None,
        colors: list[str] | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        on_sale: bool | None = None,
        sort: str | None = None,
    ) -> ProductListResponse:
        items, total = self._products.list_active_paginated(
            page=pagination.page,
            limit=pagination.limit,
            search=pagination.search,
            category_ids=category_ids,
            brand_id=brand_id,
            statuses=statuses,
            colors=colors,
            min_price=min_price,
            max_price=max_price,
            on_sale=on_sale,
            sort=sort,
        )
        return ProductListResponse(
            message="Products fetched successfully",
            data=[self._to_product_read(item) for item in items],
            meta=build_pagination_meta(
                total=total,
                page=pagination.page,
                limit=pagination.limit,
            ),
        )

    def list_low_stock(self, *, limit: int = 8) -> LowStockListResponse:
        threshold = get_settings().LOW_STOCK_THRESHOLD
        items = self._products.list_low_stock(threshold=threshold, limit=limit)
        data: list[LowStockItemRead] = []
        for item in items:
            read = self._to_product_read(item)
            data.append(
                LowStockItemRead(
                    id=read.id,
                    name=read.name,
                    stock=read.stock,
                    threshold=threshold,
                    is_out_of_stock=read.stock <= 0,
                    image_url=read.image_url
                    or next((variant.image_url for variant in read.variants if variant.image_url), None),
                )
            )
        return LowStockListResponse(
            message="Low-stock products fetched",
            threshold=threshold,
            data=data,
        )

    def get_product(self, product_id: UUID) -> ProductResponse:
        product = self._get_active_product(product_id)
        return ProductResponse(
            message="Product fetched successfully",
            product=self._to_product_read(product),
        )

    def get_related_products(
        self,
        product_id: UUID,
        *,
        limit: int = 8,
    ) -> RelatedProductsResponse:
        product = self._get_active_product(product_id)
        related = self._products.list_related(
            product_id=product.id,
            category_id=product.category_id,
            limit=limit,
        )
        return RelatedProductsResponse(
            message="Related products fetched successfully",
            data=[self._to_product_read(item) for item in related],
        )

    def create_product(self, payload: ProductCreateRequest) -> ProductResponse:
        self._ensure_category_exists(payload.category_id, require_active=True)
        self._ensure_brand_exists(payload.brand_id, require_active=True)
        self._validate_variant_sale_prices(payload.variants)

        initial_stock = (
            sum(variant.stock for variant in payload.variants)
            if payload.variants
            else payload.stock
        )
        product = self._products.create(
            name=payload.name,
            description=payload.description,
            brand_id=payload.brand_id,
            sku=payload.sku,
            price=payload.price,
            price_sale=payload.price_sale,
            colors=payload.colors,
            status=payload.status,
            stock=initial_stock,
            category_id=payload.category_id,
        )

        for variant in payload.variants:
            self._create_variant_row(product.id, variant)

        if payload.variants:
            self._sync_product_stock_from_variants(product.id)
            product = self._get_active_product(product.id)

        logger.info(
            "Created product %s with %s variant(s)",
            product.id,
            len(payload.variants),
        )

        return ProductResponse(
            message="Product created successfully",
            product=self._to_product_read(product),
        )

    def update_product(
        self,
        product_id: UUID,
        payload: ProductUpdateRequest,
    ) -> ProductResponse:
        product = self._get_active_product(product_id)
        self._ensure_category_exists(
            payload.category_id,
            require_active=payload.category_id != product.category_id,
        )
        self._ensure_brand_exists(
            payload.brand_id,
            require_active=payload.brand_id != product.brand_id,
        )

        if payload.variants is not None:
            self._validate_variant_sale_prices(payload.variants)
            stock = sum(variant.stock for variant in payload.variants)
        elif product.variants and payload.stock != product.stock:
            raise BadRequestError(
                "Cannot set product stock directly while variants exist; "
                "update variant stock instead or send variants in the payload"
            )
        else:
            stock = payload.stock

        updated = self._products.update(
            product,
            name=payload.name,
            description=payload.description,
            brand_id=payload.brand_id,
            sku=payload.sku,
            price=payload.price,
            price_sale=payload.price_sale,
            colors=payload.colors,
            status=payload.status,
            stock=stock,
            category_id=payload.category_id,
        )

        if payload.variants is not None:
            self._replace_variants(updated.id, payload.variants)
            self._sync_product_stock_from_variants(updated.id)
            updated = self._get_active_product(updated.id)

        logger.info("Updated product %s", updated.id)

        return ProductResponse(
            message="Product updated successfully",
            product=self._to_product_read(updated),
        )

    def upload_product_image(self, product_id: UUID, upload: UploadFile) -> ProductResponse:
        product = self._get_active_product(product_id)
        stored = self._images.upload(upload)
        previous_id = product.image_public_id
        updated = self._products.update_image(
            product,
            image_url=stored.url,
            image_public_id=stored.public_id,
        )
        if previous_id and previous_id != stored.public_id:
            self._images.delete(previous_id, missing_ok=True)
        logger.info("Uploaded image for product %s via %s", updated.id, stored.provider)
        return ProductResponse(
            message="Product image uploaded successfully",
            product=self._to_product_read(updated),
        )

    def delete_product_image(self, product_id: UUID) -> ProductResponse:
        product = self._get_active_product(product_id)
        if product.image_public_id:
            self._images.delete(product.image_public_id)
        updated = self._products.update_image(product, image_url=None, image_public_id=None)
        logger.info("Removed image for product %s", updated.id)
        return ProductResponse(
            message="Product image removed successfully",
            product=self._to_product_read(updated),
        )

    def delete_product(self, product_id: UUID) -> ProductResponse:
        product = self._get_active_product(product_id)
        if product.image_public_id:
            self._images.delete(product.image_public_id, missing_ok=True)
        for variant in product.variants or []:
            self._clear_variant_image(variant, missing_ok=True)
        deleted = self._products.soft_delete(product)
        logger.info("Soft deleted product %s", deleted.id)

        return ProductResponse(
            message="Product deleted successfully",
            product=self._to_product_read(deleted),
        )

    def create_variant(
        self,
        product_id: UUID,
        payload: ProductVariantCreateRequest,
    ) -> ProductVariantResponse:
        product = self._get_active_product(product_id)
        self._validate_variant_sale_prices([payload])
        variant = self._create_variant_row(product.id, payload)
        self._sync_product_stock_from_variants(product.id)
        logger.info("Created variant %s for product %s", variant.id, product.id)
        return ProductVariantResponse(
            message="Variant created successfully",
            variant=ProductVariantRead.model_validate(variant),
        )

    def update_variant(
        self,
        product_id: UUID,
        variant_id: UUID,
        payload: ProductVariantUpdateRequest,
    ) -> ProductVariantResponse:
        product = self._get_active_product(product_id)
        self._validate_variant_sale_prices([payload])
        if payload.brand_id:
            self._ensure_brand_exists(payload.brand_id, require_active=payload.brand_id != product.brand_id)
        if payload.category_id:
            self._ensure_category_exists(
                payload.category_id,
                require_active=payload.category_id != product.category_id,
            )
        variant = self._get_product_variant(product_id, variant_id)
        updated = self._variants.update(
            variant,
            name=payload.name,
            sku=payload.sku,
            color=payload.color,
            size=payload.size,
            material=payload.material,
            style=payload.style,
            brand_id=payload.brand_id or product.brand_id,
            category_id=payload.category_id or product.category_id,
            price=payload.price,
            price_sale=payload.price_sale,
            stock=payload.stock,
        )
        self._sync_product_stock_from_variants(product_id)
        logger.info("Updated variant %s", updated.id)
        return ProductVariantResponse(
            message="Variant updated successfully",
            variant=ProductVariantRead.model_validate(updated),
        )

    def upload_variant_image(
        self,
        product_id: UUID,
        variant_id: UUID,
        upload: UploadFile,
    ) -> ProductVariantResponse:
        self._get_active_product(product_id)
        variant = self._get_product_variant(product_id, variant_id)
        stored = self._images.upload(upload)
        previous_id = variant.image_public_id
        updated = self._variants.update_image(
            variant,
            image_url=stored.url,
            image_public_id=stored.public_id,
        )
        if previous_id and previous_id != stored.public_id:
            self._images.delete(previous_id, missing_ok=True)
        return ProductVariantResponse(
            message="Variant image uploaded successfully",
            variant=ProductVariantRead.model_validate(updated),
        )

    def delete_variant_image(self, product_id: UUID, variant_id: UUID) -> ProductVariantResponse:
        self._get_active_product(product_id)
        variant = self._get_product_variant(product_id, variant_id)
        self._clear_variant_image(variant)
        updated = self._get_product_variant(product_id, variant_id)
        return ProductVariantResponse(
            message="Variant image removed successfully",
            variant=ProductVariantRead.model_validate(updated),
        )

    def delete_variant(self, product_id: UUID, variant_id: UUID) -> ProductVariantResponse:
        self._get_active_product(product_id)
        variant = self._get_product_variant(product_id, variant_id)
        payload = ProductVariantRead.model_validate(variant)
        self._clear_variant_image(variant, missing_ok=True)
        self._variants.delete(variant)
        self._sync_product_stock_from_variants(product_id)
        logger.info("Deleted variant %s", variant_id)
        return ProductVariantResponse(
            message="Variant deleted successfully",
            variant=payload,
        )

    def _replace_variants(
        self,
        product_id: UUID,
        variants: list[ProductVariantUpsertRequest],
    ) -> None:
        existing = {v.id: v for v in self._variants.list_by_product(product_id)}
        keep_ids: set[UUID] = set()

        for item in variants:
            if item.id is not None and item.id in existing:
                keep_ids.add(item.id)
                self._variants.update(
                    existing[item.id],
                    name=item.name,
                    sku=item.sku,
                    color=item.color,
                    size=item.size,
                    material=item.material,
                    style=item.style,
                    brand_id=item.brand_id,
                    category_id=item.category_id,
                    price=item.price,
                    price_sale=item.price_sale,
                    stock=item.stock,
                )
            else:
                created = self._create_variant_row(product_id, item)
                keep_ids.add(created.id)

        for variant_id, variant in existing.items():
            if variant_id not in keep_ids:
                self._clear_variant_image(variant, missing_ok=True)
                self._variants.delete(variant)

    def _clear_variant_image(self, variant: ProductVariant, *, missing_ok: bool = False) -> None:
        if variant.image_public_id:
            self._images.delete(variant.image_public_id, missing_ok=missing_ok)
        self._variants.update_image(variant, image_url=None, image_public_id=None)

    def _create_variant_row(
        self,
        product_id: UUID,
        payload: ProductVariantCreateRequest | ProductVariantUpsertRequest,
    ) -> ProductVariant:
        product = self._products.get_by_id(product_id, include_deleted=True)
        if payload.brand_id:
            self._ensure_brand_exists(
                payload.brand_id,
                require_active=payload.brand_id != (product.brand_id if product else None),
            )
        if payload.category_id:
            self._ensure_category_exists(
                payload.category_id,
                require_active=payload.category_id != (product.category_id if product else None),
            )
        return self._variants.create(
            product_id=product_id,
            name=payload.name,
            sku=payload.sku,
            color=payload.color,
            size=payload.size,
            material=payload.material,
            style=payload.style,
            brand_id=payload.brand_id or (product.brand_id if product else None),
            category_id=payload.category_id or (product.category_id if product else None),
            price=payload.price,
            price_sale=payload.price_sale,
            stock=payload.stock,
        )

    def _validate_variant_sale_prices(
        self,
        variants: list[ProductVariantCreateRequest]
        | list[ProductVariantUpsertRequest]
        | list[ProductVariantUpdateRequest],
    ) -> None:
        for variant in variants:
            if (
                variant.price_sale is not None
                and variant.price is not None
                and variant.price_sale >= variant.price
            ):
                raise BadRequestError("Variant priceSale must be less than variant price")

    def _sync_product_stock_from_variants(self, product_id: UUID) -> None:
        product = self._products.get_by_id(product_id, include_deleted=True)
        if product is None:
            return
        if self._variants.count_by_product(product_id) == 0:
            return
        total = self._variants.sum_stock_by_product(product_id)
        self._products.update(
            product,
            name=product.name,
            description=product.description,
            brand_id=product.brand_id,
            sku=product.sku,
            price=product.price,
            price_sale=product.price_sale,
            colors=list(product.colors or []),
            status=product.status or "",
            stock=total,
            category_id=product.category_id,
        )

    def _to_product_read(self, product: Product) -> ProductRead:
        variants = [ProductVariantRead.model_validate(v) for v in (product.variants or [])]
        stock = sum(v.stock for v in variants) if variants else product.stock
        data = ProductRead.model_validate(product)
        return data.model_copy(
            update={
                "variants": variants,
                "stock": stock,
                "has_variants": bool(variants),
                "colors": list(product.colors or []),
                "brand": product.brand_record.name if product.brand_record else None,
                "brand_id": product.brand_id,
            }
        )

    def _get_active_product(self, product_id: UUID) -> Product:
        product = self._products.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return product

    def _get_product_variant(self, product_id: UUID, variant_id: UUID) -> ProductVariant:
        variant = self._variants.get_by_id(variant_id)
        if variant is None or variant.product_id != product_id:
            raise NotFoundError("Variant not found")
        return variant

    def _ensure_category_exists(self, category_id: UUID, *, require_active: bool = True) -> None:
        category = self._categories.get_by_id(category_id)
        if category is None:
            raise NotFoundError("Category not found")
        if require_active and not category.is_active:
            raise BadRequestError("Category is inactive")

    def _ensure_brand_exists(self, brand_id: UUID | None, *, require_active: bool = True) -> None:
        if brand_id is None:
            return
        brand = self._brands.get_by_id(brand_id)
        if brand is None:
            raise NotFoundError("Brand not found")
        if require_active and not brand.is_active:
            raise BadRequestError("Brand is inactive")
