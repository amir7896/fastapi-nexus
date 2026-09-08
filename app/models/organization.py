import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import UserRole


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    timezone: Mapped[str] = mapped_column(String(60), nullable=False, default="UTC")
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    shipping_flat_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    notify_orders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_low_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shop_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    plan_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    stripe_billing_customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
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

    memberships = relationship("OrganizationMembership", back_populates="organization")


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_org"),
    )

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
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", lazy="joined")


class OrganizationInvite(Base):
    __tablename__ = "organization_invites"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    organization = relationship("Organization", lazy="joined")
    invited_by = relationship("User", lazy="joined")
