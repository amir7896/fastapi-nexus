import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CouponType(str, Enum):
    PERCENT = "percent"
    FIXED = "fixed"


class Coupon(Base):
    __tablename__ = "coupons"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_coupons_org_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default=CouponType.PERCENT.value)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
