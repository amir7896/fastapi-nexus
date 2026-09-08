from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tenant import apply_organization_filter, require_organization_id, visible_in_organization
from app.models.category import Category


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _active_filters(self, search: str | None = None, is_active: bool | None = None) -> list:
        filters = [Category.deleted_at.is_(None)]
        apply_organization_filter(filters, Category.organization_id, self._db)
        if search:
            filters.append(Category.name.ilike(f"%{search}%"))
        if is_active is not None:
            filters.append(Category.is_active.is_(is_active))
        return filters

    def list_active_paginated(
        self,
        *,
        page: int,
        limit: int,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Category], int]:
        filters = self._active_filters(search, is_active)
        total = self._db.scalar(select(func.count(Category.id)).where(*filters)) or 0

        offset = (page - 1) * limit
        stmt = (
            select(Category)
            .where(*filters)
            .order_by(Category.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(self._db.scalars(stmt).all())
        return items, total

    def get_by_id(self, category_id: UUID, *, include_deleted: bool = False) -> Category | None:
        category = self._db.get(Category, category_id)
        if category is None:
            return None
        if not include_deleted and category.deleted_at is not None:
            return None
        if not visible_in_organization(category, self._db):
            return None
        return category

    def get_active_by_name(self, name: str) -> Category | None:
        filters = [Category.name == name.strip(), Category.deleted_at.is_(None)]
        apply_organization_filter(filters, Category.organization_id, self._db)
        return self._db.scalar(select(Category).where(*filters))

    def name_exists(self, name: str, *, exclude_id: UUID | None = None) -> bool:
        filters = [Category.name == name.strip(), Category.deleted_at.is_(None)]
        apply_organization_filter(filters, Category.organization_id, self._db)
        stmt = select(Category.id).where(*filters)
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        return self._db.scalar(stmt) is not None

    def create(self, *, name: str, is_active: bool = True) -> Category:
        now = datetime.now(timezone.utc)
        category = Category(
            name=name.strip(),
            organization_id=require_organization_id(self._db),
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        self._db.add(category)
        self._db.commit()
        self._db.refresh(category)
        return category

    def update(
        self,
        category: Category,
        *,
        name: str | None = None,
        is_active: bool | None = None,
    ) -> Category:
        if name is not None:
            category.name = name.strip()
        if is_active is not None:
            category.is_active = is_active
        category.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(category)
        return category

    def soft_delete(self, category: Category) -> Category:
        now = datetime.now(timezone.utc)
        category.deleted_at = now
        category.updated_at = now
        self._db.commit()
        self._db.refresh(category)
        return category
