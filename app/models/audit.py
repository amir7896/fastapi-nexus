import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StaffAuditLog(Base):
    __tablename__ = "staff_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    actor_name: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    actor = relationship("User", lazy="joined")
