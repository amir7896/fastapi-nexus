from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderItem, OrderStatus

FIRST_ORDER_NUMBER = 1001


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _list_filters(
        self,
        *,
        user_id: UUID | None = None,
        status: OrderStatus | None = None,
        search: str | None = None,
    ) -> list:
        filters = []
        if user_id is not None:
            filters.append(Order.user_id == user_id)
        if status is not None:
            filters.append(Order.status == status)
        order_number = self._parse_order_number(search)
        if order_number is not None:
            filters.append(Order.order_number == order_number)
        return filters

    def _parse_order_number(self, search: str | None) -> int | None:
        if not search:
            return None
        digits = search.strip().lstrip("#")
        if digits.isdigit():
            return int(digits)
        return None

    def _allocate_order_number(self) -> int:
        latest = self._db.scalar(
            select(Order.order_number)
            .order_by(Order.order_number.desc())
            .limit(1)
            .with_for_update()
        )
        return (latest or FIRST_ORDER_NUMBER - 1) + 1

    def list_paginated(
        self,
        *,
        page: int,
        limit: int,
        user_id: UUID | None = None,
        status: OrderStatus | None = None,
        search: str | None = None,
    ) -> tuple[list[Order], int]:
        filters = self._list_filters(user_id=user_id, status=status, search=search)
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
        shipping: dict | None = None,
    ) -> Order:
        now = datetime.now(timezone.utc)
        shipping = shipping or {}

        order = Order(
            user_id=user_id,
            order_number=self._allocate_order_number(),
            status=OrderStatus.PENDING,
            subtotal=subtotal,
            stripe_fee=stripe_fee,
            total=total,
            shipping_name=shipping.get("name"),
            shipping_phone=shipping.get("phone"),
            shipping_address=shipping.get("address"),
            shipping_city=shipping.get("city"),
            shipping_country=shipping.get("country"),
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

    def update_status(
        self,
        order: Order,
        *,
        status: OrderStatus,
        tracking_number: str | None = None,
    ) -> Order:
        order.status = status
        if tracking_number is not None:
            order.tracking_number = tracking_number.strip() or None
        order.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        refreshed = self.get_by_id(order.id)
        assert refreshed is not None
        return refreshed

    def save(self, order: Order) -> Order:
        order.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        refreshed = self.get_by_id(order.id)
        assert refreshed is not None
        return refreshed

    def set_shipping(self, order: Order, *, shipping: dict) -> Order:
        order.shipping_name = shipping["name"]
        order.shipping_phone = shipping["phone"]
        order.shipping_address = shipping["address"]
        order.shipping_city = shipping["city"]
        order.shipping_country = shipping["country"]
        order.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        refreshed = self.get_by_id(order.id)
        assert refreshed is not None
        return refreshed
