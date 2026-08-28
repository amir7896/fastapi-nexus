from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.cart import CartItem


class CartRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_user(self, user_id: UUID) -> list[CartItem]:
        stmt = (
            select(CartItem)
            .options(selectinload(CartItem.product))
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        )
        return list(self._db.scalars(stmt).all())

    def get_item(self, user_id: UUID, product_id: UUID) -> CartItem | None:
        stmt = select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
        return self._db.scalar(stmt)

    def add_item(self, *, user_id: UUID, product_id: UUID, quantity: int) -> CartItem:
        existing = self.get_item(user_id, product_id)
        now = datetime.now(timezone.utc)

        if existing is not None:
            existing.quantity += quantity
            existing.updated_at = now
            self._db.commit()
            self._db.refresh(existing)
            return existing

        item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            created_at=now,
            updated_at=now,
        )
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return item

    def set_quantity(self, item: CartItem, *, quantity: int) -> CartItem:
        item.quantity = quantity
        item.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(item)
        return item

    def remove_item(self, item: CartItem) -> None:
        self._db.delete(item)
        self._db.commit()

    def clear(self, user_id: UUID) -> None:
        items = self.list_by_user(user_id)
        for item in items:
            self._db.delete(item)
        self._db.commit()
