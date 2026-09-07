from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.product_variant import ProductVariant


class ProductVariantRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_product(self, product_id: UUID) -> list[ProductVariant]:
        stmt = (
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.created_at.asc())
        )
        return list(self._db.scalars(stmt).all())

    def get_by_id(self, variant_id: UUID) -> ProductVariant | None:
        return self._db.get(ProductVariant, variant_id)

    def create(
        self,
        *,
        product_id: UUID,
        name: str,
        sku: str | None,
        color: str | None,
        size: str | None,
        material: str | None,
        style: str | None,
        brand_id: UUID | None = None,
        category_id: UUID | None = None,
        price: Decimal | None,
        price_sale: Decimal | None = None,
        stock: int,
    ) -> ProductVariant:
        now = datetime.now(timezone.utc)
        variant = ProductVariant(
            product_id=product_id,
            name=name.strip(),
            sku=sku.strip() if sku else None,
            color=color.strip() if color else None,
            size=size.strip() if size else None,
            material=material.strip() if material else None,
            style=style.strip() if style else None,
            brand_id=brand_id,
            category_id=category_id,
            price=price,
            price_sale=price_sale,
            stock=stock,
            created_at=now,
            updated_at=now,
        )
        self._db.add(variant)
        self._db.commit()
        self._db.refresh(variant)
        return variant

    def update(
        self,
        variant: ProductVariant,
        *,
        name: str,
        sku: str | None,
        color: str | None,
        size: str | None,
        material: str | None,
        style: str | None,
        brand_id: UUID | None = None,
        category_id: UUID | None = None,
        price: Decimal | None,
        price_sale: Decimal | None = None,
        stock: int,
    ) -> ProductVariant:
        variant.name = name.strip()
        variant.sku = sku.strip() if sku else None
        variant.color = color.strip() if color else None
        variant.size = size.strip() if size else None
        variant.material = material.strip() if material else None
        variant.style = style.strip() if style else None
        variant.brand_id = brand_id
        variant.category_id = category_id
        variant.price = price
        variant.price_sale = price_sale
        variant.stock = stock
        variant.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(variant)
        return variant

    def update_image(
        self,
        variant: ProductVariant,
        *,
        image_url: str | None,
        image_public_id: str | None,
    ) -> ProductVariant:
        variant.image_url = image_url
        variant.image_public_id = image_public_id
        variant.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(variant)
        return variant

    def delete(self, variant: ProductVariant) -> None:
        self._db.delete(variant)
        self._db.commit()

    def delete_by_product(self, product_id: UUID) -> None:
        for variant in self.list_by_product(product_id):
            self._db.delete(variant)
        self._db.commit()

    def count_by_product(self, product_id: UUID) -> int:
        return (
            self._db.scalar(
                select(func.count(ProductVariant.id)).where(
                    ProductVariant.product_id == product_id
                )
            )
            or 0
        )

    def sum_stock_by_product(self, product_id: UUID) -> int:
        return (
            self._db.scalar(
                select(func.coalesce(func.sum(ProductVariant.stock), 0)).where(
                    ProductVariant.product_id == product_id
                )
            )
            or 0
        )

    def decrement_stock(self, variant_id: UUID, quantity: int) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(ProductVariant)
            .where(
                ProductVariant.id == variant_id,
                ProductVariant.stock >= quantity,
            )
            .values(
                stock=ProductVariant.stock - quantity,
                updated_at=now,
            )
        )
        result = self._db.execute(stmt)
        self._db.commit()
        return bool(result.rowcount)

    def increment_stock(self, variant_id: UUID, quantity: int) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(ProductVariant)
            .where(ProductVariant.id == variant_id)
            .values(
                stock=ProductVariant.stock + quantity,
                updated_at=now,
            )
        )
        self._db.execute(stmt)
        self._db.commit()
