from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.tenant import require_organization_id
from app.models.product import Product
from app.models.wishlist import WishlistItem


class WishlistRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_ids(self, user_id: UUID) -> list[UUID]:
        stmt = (
            select(WishlistItem.product_id)
            .join(Product, Product.id == WishlistItem.product_id)
            .where(
                WishlistItem.user_id == user_id,
                WishlistItem.organization_id == require_organization_id(self._db),
                Product.deleted_at.is_(None),
            )
            .order_by(WishlistItem.created_at.desc())
        )
        return list(self._db.scalars(stmt).all())

    def list_items(self, user_id: UUID) -> list[WishlistItem]:
        stmt = (
            select(WishlistItem)
            .join(Product, Product.id == WishlistItem.product_id)
            .options(selectinload(WishlistItem.product))
            .where(
                WishlistItem.user_id == user_id,
                WishlistItem.organization_id == require_organization_id(self._db),
                Product.deleted_at.is_(None),
            )
            .order_by(WishlistItem.created_at.desc())
        )
        return list(self._db.scalars(stmt).unique().all())

    def get_item(self, user_id: UUID, product_id: UUID) -> WishlistItem | None:
        stmt = select(WishlistItem).where(
            WishlistItem.user_id == user_id,
            WishlistItem.product_id == product_id,
            WishlistItem.organization_id == require_organization_id(self._db),
        )
        return self._db.scalar(stmt)

    def add(self, *, user_id: UUID, product_id: UUID) -> WishlistItem:
        existing = self.get_item(user_id, product_id)
        if existing is not None:
            return existing
        item = WishlistItem(
            user_id=user_id,
            organization_id=require_organization_id(self._db),
            product_id=product_id,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return item

    def remove(self, item: WishlistItem) -> None:
        self._db.delete(item)
        self._db.commit()
