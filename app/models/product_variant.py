import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    material: Mapped[str | None] = mapped_column(String(50), nullable=True)
    style: Mapped[str | None] = mapped_column(String(50), nullable=True)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_sale: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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

    product = relationship("Product", back_populates="variants")
    brand_record = relationship("Brand", lazy="joined")
    category_record = relationship("Category", lazy="joined")
