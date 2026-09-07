from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.models.brand import Brand
from app.models.product import Product


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _active_filters(
        self,
        *,
        search: str | None = None,
        category_id: UUID | None = None,
        brand_id: UUID | None = None,
        status: str | None = None,
        colors: list[str] | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        on_sale: bool | None = None,
    ) -> list:
        filters = [Product.deleted_at.is_(None)]
        if search:
            filters.append(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.sku.ilike(f"%{search}%"),
                    Product.brand_id.in_(select(Brand.id).where(Brand.name.ilike(f"%{search}%"))),
                )
            )
        if category_id is not None:
            filters.append(Product.category_id == category_id)
        if brand_id is not None:
            filters.append(Product.brand_id == brand_id)
        if status is not None and status != "":
            filters.append(Product.status == status)
        if colors:
            # JSON array contains any of the requested colors (MySQL JSON_CONTAINS style via OR).
            color_clauses = []
            for color in colors:
                color_clauses.append(func.json_contains(Product.colors, f'"{color}"'))
            if color_clauses:
                filters.append(or_(*color_clauses))
        if min_price is not None:
            filters.append(Product.price >= min_price)
        if max_price is not None:
            filters.append(Product.price <= max_price)
        if on_sale is True:
            filters.append(
                or_(
                    Product.status == "sale",
                    Product.price_sale.is_not(None),
                )
            )
        return filters

    def _order_by(self, sort: str | None):
        if sort == "priceAsc":
            return Product.price.asc()
        if sort == "priceDesc":
            return Product.price.desc()
        if sort == "nameAsc":
            return Product.name.asc()
        return Product.created_at.desc()

    def list_active_paginated(
        self,
        *,
        page: int,
        limit: int,
        search: str | None = None,
        category_id: UUID | None = None,
        brand_id: UUID | None = None,
        status: str | None = None,
        colors: list[str] | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        on_sale: bool | None = None,
        sort: str | None = None,
    ) -> tuple[list[Product], int]:
        filters = self._active_filters(
            search=search,
            category_id=category_id,
            brand_id=brand_id,
            status=status,
            colors=colors,
            min_price=min_price,
            max_price=max_price,
            on_sale=on_sale,
        )
        total = self._db.scalar(select(func.count(Product.id)).where(*filters)) or 0

        offset = (page - 1) * limit
        stmt = (
            select(Product)
            .where(*filters)
            .order_by(self._order_by(sort))
            .offset(offset)
            .limit(limit)
        )
        items = list(self._db.scalars(stmt).all())
        return items, total

    def list_related(
        self,
        *,
        product_id: UUID,
        category_id: UUID,
        limit: int,
    ) -> list[Product]:
        stmt = (
            select(Product)
            .where(
                Product.deleted_at.is_(None),
                Product.id != product_id,
                Product.category_id == category_id,
            )
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        related = list(self._db.scalars(stmt).all())
        if related:
            return related

        fallback = (
            select(Product)
            .where(
                Product.deleted_at.is_(None),
                Product.id != product_id,
            )
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(fallback).all())

    def get_by_id(self, product_id: UUID, *, include_deleted: bool = False) -> Product | None:
        product = self._db.get(Product, product_id)
        if product is None:
            return None
        if not include_deleted and product.deleted_at is not None:
            return None
        return product

    def create(
        self,
        *,
        name: str,
        description: str | None,
        brand_id: UUID | None,
        sku: str | None,
        price: Decimal,
        price_sale: Decimal | None,
        colors: list[str],
        status: str,
        stock: int,
        category_id: UUID,
    ) -> Product:
        now = datetime.now(timezone.utc)
        product = Product(
            name=name.strip(),
            description=description.strip() if description else None,
            brand_id=brand_id,
            sku=sku.strip() if sku else None,
            price=price,
            price_sale=price_sale,
            colors=list(colors or []),
            status=status or "",
            stock=stock,
            category_id=category_id,
            created_at=now,
            updated_at=now,
        )
        self._db.add(product)
        self._db.commit()
        self._db.refresh(product)
        return product

    def update(
        self,
        product: Product,
        *,
        name: str,
        description: str | None,
        brand_id: UUID | None,
        sku: str | None,
        price: Decimal,
        price_sale: Decimal | None,
        colors: list[str],
        status: str,
        stock: int,
        category_id: UUID,
    ) -> Product:
        product.name = name.strip()
        product.description = description.strip() if description else None
        product.brand_id = brand_id
        product.sku = sku.strip() if sku else None
        product.price = price
        product.price_sale = price_sale
        product.colors = list(colors or [])
        product.status = status or ""
        product.stock = stock
        product.category_id = category_id
        product.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(product)
        return product

    def update_image(
        self,
        product: Product,
        *,
        image_url: str | None,
        image_public_id: str | None,
    ) -> Product:
        product.image_url = image_url
        product.image_public_id = image_public_id
        product.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(product)
        return product

    def decrement_stock(self, product_id: UUID, quantity: int) -> bool:
        """Atomically reduce stock if enough units remain. Returns False if not."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Product)
            .where(
                Product.id == product_id,
                Product.deleted_at.is_(None),
                Product.stock >= quantity,
            )
            .values(
                stock=Product.stock - quantity,
                updated_at=now,
            )
        )
        result = self._db.execute(stmt)
        self._db.commit()
        return bool(result.rowcount)

    def increment_stock(self, product_id: UUID, quantity: int) -> None:
        """Restore stock (e.g. if a later line item fails to reserve)."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Product)
            .where(
                Product.id == product_id,
                Product.deleted_at.is_(None),
            )
            .values(
                stock=Product.stock + quantity,
                updated_at=now,
            )
        )
        self._db.execute(stmt)
        self._db.commit()

    def soft_delete(self, product: Product) -> Product:
        now = datetime.now(timezone.utc)
        product.deleted_at = now
        product.updated_at = now
        self._db.commit()
        self._db.refresh(product)
        return product
