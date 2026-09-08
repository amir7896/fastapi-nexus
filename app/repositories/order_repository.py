from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.tenant import apply_organization_filter, require_organization_id, visible_in_organization
from app.models.order import Order, OrderItem, OrderStatus, ReturnStatus

_PAID_STATUSES = (
    OrderStatus.PAID,
    OrderStatus.PROCESSING,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
    OrderStatus.RETURNED,
)

FIRST_ORDER_NUMBER = 1001


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _list_filters(
        self,
        *,
        user_id: UUID | None = None,
        status: OrderStatus | None = None,
        return_status: ReturnStatus | None = None,
        search: str | None = None,
    ) -> list:
        filters = []
        apply_organization_filter(filters, Order.organization_id, self._db)
        if user_id is not None:
            filters.append(Order.user_id == user_id)
        if status is not None:
            filters.append(Order.status == status)
        if return_status is not None:
            filters.append(Order.return_status == return_status.value)
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
        return_status: ReturnStatus | None = None,
        search: str | None = None,
    ) -> tuple[list[Order], int]:
        filters = self._list_filters(
            user_id=user_id,
            status=status,
            return_status=return_status,
            search=search,
        )
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
        order = self._db.scalar(stmt)
        if order is None or not visible_in_organization(order, self._db):
            return None
        return order

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
        coupon_code: str | None = None,
        discount_amount: Decimal | None = None,
    ) -> Order:
        now = datetime.now(timezone.utc)
        shipping = shipping or {}

        order = Order(
            user_id=user_id,
            organization_id=require_organization_id(self._db),
            order_number=self._allocate_order_number(),
            status=OrderStatus.PENDING,
            subtotal=subtotal,
            discount_amount=discount_amount or Decimal("0.00"),
            coupon_code=coupon_code,
            stripe_fee=stripe_fee,
            total=total,
            shipping_name=shipping.get("name"),
            shipping_phone_country_code=shipping.get("phone_country_code"),
            shipping_phone=shipping.get("phone"),
            shipping_address=shipping.get("address"),
            shipping_city=shipping.get("city"),
            shipping_state=shipping.get("state"),
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
        shipping_carrier: str | None = None,
        shipped_at: datetime | None = None,
    ) -> Order:
        order.status = status
        if tracking_number is not None:
            order.tracking_number = tracking_number.strip() or None
        if shipping_carrier is not None:
            order.shipping_carrier = shipping_carrier
        if shipped_at is not None:
            order.shipped_at = shipped_at
        order.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        refreshed = self.get_by_id(order.id)
        assert refreshed is not None
        return refreshed

    def list_stale_shipped(self, *, cutoff: datetime) -> list[Order]:
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.status == OrderStatus.SHIPPED,
                or_(
                    and_(Order.shipped_at.is_not(None), Order.shipped_at <= cutoff),
                    and_(Order.shipped_at.is_(None), Order.updated_at <= cutoff),
                ),
            )
        )
        return list(self._db.scalars(stmt).all())

    def save(self, order: Order) -> Order:
        order.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        refreshed = self.get_by_id(order.id)
        assert refreshed is not None
        return refreshed

    def set_shipping(self, order: Order, *, shipping: dict) -> Order:
        order.shipping_name = shipping["name"]
        order.shipping_phone_country_code = shipping.get("phone_country_code")
        order.shipping_phone = shipping["phone"]
        order.shipping_address = shipping["address"]
        order.shipping_city = shipping["city"]
        order.shipping_state = shipping.get("state")
        order.shipping_country = shipping["country"]
        order.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        refreshed = self.get_by_id(order.id)
        assert refreshed is not None
        return refreshed

    def get_delivered_for_product(self, *, user_id: UUID, product_id: UUID) -> Order | None:
        stmt = (
            select(Order)
            .join(OrderItem)
            .where(
                Order.user_id == user_id,
                Order.status == OrderStatus.DELIVERED,
                OrderItem.product_id == product_id,
            )
            .order_by(Order.delivered_at.desc(), Order.updated_at.desc())
            .limit(1)
        )
        return self._db.scalar(stmt)

    def has_purchase_of_product(self, *, user_id: UUID, product_id: UUID) -> bool:
        stmt = (
            select(func.count(Order.id))
            .join(OrderItem)
            .where(
                Order.user_id == user_id,
                Order.status != OrderStatus.CANCELLED,
                OrderItem.product_id == product_id,
            )
        )
        return bool(self._db.scalar(stmt))

    def report_summary(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> tuple[dict, dict[date, dict], dict[date, Decimal]]:
        paid_filter = or_(
            Order.status.in_(_PAID_STATUSES),
            and_(
                Order.status == OrderStatus.CANCELLED,
                Order.stripe_payment_intent_id.is_not(None),
            ),
        )
        org_filters = []
        apply_organization_filter(org_filters, Order.organization_id, self._db)
        sales_row = self._db.execute(
            select(
                func.count(Order.id),
                func.coalesce(func.sum(Order.total), 0),
                func.coalesce(func.sum(Order.stripe_fee), 0),
            ).where(Order.created_at >= start, Order.created_at < end, paid_filter, *org_filters)
        ).one()
        refund_total = self._db.scalar(
            select(func.coalesce(func.sum(Order.amount_refunded), 0)).where(
                Order.refunded_at.is_not(None),
                Order.refunded_at >= start,
                Order.refunded_at < end,
                *org_filters,
            )
        ) or 0
        totals = {
            "order_count": sales_row[0] or 0,
            "sales": sales_row[1] or 0,
            "stripe_fees": sales_row[2] or 0,
            "refunds": refund_total,
        }

        day_expr = func.date(Order.created_at)
        sales_days: dict[date, dict] = {}
        for day, count, sales, fees in self._db.execute(
            select(
                day_expr,
                func.count(Order.id),
                func.coalesce(func.sum(Order.total), 0),
                func.coalesce(func.sum(Order.stripe_fee), 0),
            )
            .where(Order.created_at >= start, Order.created_at < end, paid_filter, *org_filters)
            .group_by(day_expr)
        ).all():
            sales_days[_as_date(day)] = {
                "order_count": count or 0,
                "sales": sales or 0,
                "stripe_fees": fees or 0,
            }

        refund_days: dict[date, Decimal] = {}
        refund_day = func.date(Order.refunded_at)
        for day, amount in self._db.execute(
            select(refund_day, func.coalesce(func.sum(Order.amount_refunded), 0))
            .where(
                Order.refunded_at.is_not(None),
                Order.refunded_at >= start,
                Order.refunded_at < end,
                *org_filters,
            )
            .group_by(refund_day)
        ).all():
            refund_days[_as_date(day)] = amount or 0

        return totals, sales_days, refund_days


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
