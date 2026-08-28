from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _active_filters(self, search: str | None = None) -> list:
        filters = [Category.deleted_at.is_(None)]
        if search:
            filters.append(Category.name.ilike(f"%{search}%"))
        return filters

    def list_active_paginated(
        self,
        *,
        page: int,
        limit: int,
        search: str | None = None,
    ) -> tuple[list[Category], int]:
        filters = self._active_filters(search)
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
        return category

    def get_active_by_name(self, name: str) -> Category | None:
        stmt = select(Category).where(
            Category.name == name.strip(),
            Category.deleted_at.is_(None),
        )
        return self._db.scalar(stmt)

    def name_exists(self, name: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(Category.id).where(
            Category.name == name.strip(),
            Category.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        return self._db.scalar(stmt) is not None

    def create(self, *, name: str) -> Category:
        now = datetime.now(timezone.utc)
        category = Category(
            name=name.strip(),
            created_at=now,
            updated_at=now,
        )
        self._db.add(category)
        self._db.commit()
        self._db.refresh(category)
        return category

    def update(self, category: Category, *, name: str) -> Category:
        category.name = name.strip()
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
