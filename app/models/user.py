import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    FINANCE = "FINANCE"
    SUPPORT = "SUPPORT"
    FULFILLMENT = "FULFILLMENT"


STAFF_ROLES = {
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.FINANCE,
    UserRole.SUPPORT,
    UserRole.FULFILLMENT,
}
CATALOG_ROLES = {UserRole.ADMIN, UserRole.MANAGER}
ORDER_ROLES = {UserRole.ADMIN, UserRole.MANAGER, UserRole.FINANCE, UserRole.FULFILLMENT}
SUPPORT_STAFF_ROLES = {UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPPORT}


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.USER,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES

    @property
    def can_manage_catalog(self) -> bool:
        return self.role in CATALOG_ROLES

    @property
    def can_manage_orders(self) -> bool:
        return self.role in ORDER_ROLES

    @property
    def can_manage_support(self) -> bool:
        return self.role in SUPPORT_STAFF_ROLES

    @property
    def can_manage_users(self) -> bool:
        return self.role is UserRole.ADMIN
