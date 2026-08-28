from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Session  # pyright: ignore[reportMissingImports]

from app.models.product import Product


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _active_filters(
        self,
        *,
        search: str | None = None,
        category_id: UUID | None = None,
    ) -> list:
        filters = [Product.deleted_at.is_(None)]
        if search:
            filters.append(Product.name.ilike(f"%{search}%"))
        if category_id is not None:
            filters.append(Product.category_id == category_id)
        return filters

    def list_active_paginated(
        self,
        *,
        page: int,
        limit: int,
        search: str | None = None,
        category_id: UUID | None = None,
    ) -> tuple[list[Product], int]:
        filters = self._active_filters(search=search, category_id=category_id)
        total = self._db.scalar(select(func.count(Product.id)).where(*filters)) or 0

        offset = (page - 1) * limit
        stmt = (
            select(Product)
            .where(*filters)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(self._db.scalars(stmt).all())
        return items, total

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
        price: Decimal,
        category_id: UUID,
    ) -> Product:
        now = datetime.now(timezone.utc)
        product = Product(
            name=name.strip(),
            description=description.strip() if description else None,
            price=price,
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
        price: Decimal,
        category_id: UUID,
    ) -> Product:
        product.name = name.strip()
        product.description = description.strip() if description else None
        product.price = price
        product.category_id = category_id
        product.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(product)
        return product

    def soft_delete(self, product: Product) -> Product:
        now = datetime.now(timezone.utc)
        product.deleted_at = now
        product.updated_at = now
        self._db.commit()
        self._db.refresh(product)
        return product
