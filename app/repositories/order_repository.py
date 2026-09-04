from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderItem, OrderStatus


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _list_filters(
        self,
        *,
        user_id: UUID | None = None,
        status: OrderStatus | None = None,
    ) -> list:
        filters = []
        if user_id is not None:
            filters.append(Order.user_id == user_id)
        if status is not None:
            filters.append(Order.status == status)
        return filters

    def list_paginated(
        self,
        *,
        page: int,
        limit: int,
        user_id: UUID | None = None,
        status: OrderStatus | None = None,
    ) -> tuple[list[Order], int]:
        filters = self._list_filters(user_id=user_id, status=status)
        count_stmt = select(func.count(Order.id))
        list_stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
        )
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = self._db.scalar(count_stmt) or 0
        offset = (page - 1) * limit
        items = list(
            self._db.scalars(list_stmt.offset(offset).limit(limit)).all()
        )
        return items, total

    def get_by_id(self, order_id: UUID) -> Order | None:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
            )
            .where(Order.id == order_id)
        )
        return self._db.scalar(stmt)

    def get_by_checkout_session_id(self, session_id: str) -> Order | None:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(Order.stripe_checkout_session_id == session_id)
        )
        return self._db.scalar(stmt)

    def get_by_payment_intent_id(self, payment_intent_id: str) -> Order | None:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(Order.stripe_payment_intent_id == payment_intent_id)
        )
        return self._db.scalar(stmt)

    def set_checkout_session(self, order: Order, *, session_id: str) -> Order:
        order.stripe_checkout_session_id = session_id
        order.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        refreshed = self.get_by_id(order.id)
        assert refreshed is not None
        return refreshed

    def create(
        self,
        *,
        user_id: UUID,
        line_items: list[dict],
        subtotal: Decimal,
        stripe_fee: Decimal,
        total: Decimal,
    ) -> Order:
        now = datetime.now(timezone.utc)

        order = Order(
            user_id=user_id,
            status=OrderStatus.PENDING,
            subtotal=subtotal,
            stripe_fee=stripe_fee,
            total=total,
            created_at=now,
            updated_at=now,
        )
        self._db.add(order)
        self._db.flush()

        for item in line_items:
            self._db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=item["product_id"],
                    variant_id=item.get("variant_id"),
                    variant_name=item.get("variant_name"),
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    subtotal=item["subtotal"],
                )
            )

        self._db.commit()
        created = self.get_by_id(order.id)
        assert created is not None
        return created

    def update_payment_details(
        self,
        order: Order,
        *,
        status: OrderStatus | None = None,
        payment_intent_id: str | None = None,
        payment_method_id: str | None = None,
    ) -> Order:
        if status is not None:
            order.status = status
        if payment_intent_id is not None:
            order.stripe_payment_intent_id = payment_intent_id
        if payment_method_id is not None:
            order.stripe_payment_method_id = payment_method_id
        order.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        refreshed = self.get_by_id(order.id)
        assert refreshed is not None
        return refreshed

    def update_status(self, order: Order, *, status: OrderStatus) -> Order:
        order.status = status
        order.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        refreshed = self.get_by_id(order.id)
        assert refreshed is not None
        return refreshed
