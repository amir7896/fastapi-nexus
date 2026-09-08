import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_sale: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    colors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    low_stock_alerted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    category = relationship("Category", lazy="joined")
    brand_record = relationship("Brand", lazy="joined")
    variants = relationship(
        "ProductVariant",
        back_populates="product",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ProductVariant.created_at",
    )
