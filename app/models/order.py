import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


class ReturnStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    order_number: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.PENDING,
    )
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    stripe_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stripe_payment_method_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    shipping_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    shipping_phone_country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    shipping_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    shipping_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shipping_city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    shipping_state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    shipping_country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_carrier: Mapped[str | None] = mapped_column(String(40), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    amount_refunded: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    stripe_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    return_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    return_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    return_details: Mapped[str | None] = mapped_column(String(500), nullable=True)
    return_admin_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", lazy="joined")
    items = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    variant_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", lazy="joined")
    variant = relationship("ProductVariant", lazy="joined")
