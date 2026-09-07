from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.brand import Brand


class BrandRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _active_filters(self, search: str | None = None, is_active: bool | None = None) -> list:
        filters = [Brand.deleted_at.is_(None)]
        if search:
            filters.append(Brand.name.ilike(f"%{search}%"))
        if is_active is not None:
            filters.append(Brand.is_active.is_(is_active))
        return filters

    def list_active_paginated(
        self,
        *,
        page: int,
        limit: int,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Brand], int]:
        filters = self._active_filters(search, is_active)
        total = self._db.scalar(select(func.count(Brand.id)).where(*filters)) or 0
        offset = (page - 1) * limit
        stmt = (
            select(Brand)
            .where(*filters)
            .order_by(Brand.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._db.scalars(stmt).all()), total

    def get_by_id(self, brand_id: UUID, *, include_deleted: bool = False) -> Brand | None:
        brand = self._db.get(Brand, brand_id)
        if brand is None:
            return None
        if not include_deleted and brand.deleted_at is not None:
            return None
        return brand

    def name_exists(self, name: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(Brand.id).where(Brand.name == name.strip(), Brand.deleted_at.is_(None))
        if exclude_id is not None:
            stmt = stmt.where(Brand.id != exclude_id)
        return self._db.scalar(stmt) is not None

    def create(self, *, name: str, is_active: bool = True) -> Brand:
        now = datetime.now(timezone.utc)
        brand = Brand(name=name.strip(), is_active=is_active, created_at=now, updated_at=now)
        self._db.add(brand)
        self._db.commit()
        self._db.refresh(brand)
        return brand

    def update(
        self,
        brand: Brand,
        *,
        name: str | None = None,
        is_active: bool | None = None,
    ) -> Brand:
        if name is not None:
            brand.name = name.strip()
        if is_active is not None:
            brand.is_active = is_active
        brand.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(brand)
        return brand

    def soft_delete(self, brand: Brand) -> Brand:
        now = datetime.now(timezone.utc)
        brand.deleted_at = now
        brand.updated_at = now
        self._db.commit()
        self._db.refresh(brand)
        return brand
