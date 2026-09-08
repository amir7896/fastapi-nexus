import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SupportContextType(str, Enum):
    GENERAL = "GENERAL"
    ORDER = "ORDER"
    PRODUCT = "PRODUCT"


class SupportConversationStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class SupportChannel(str, Enum):
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"


class SupportConversation(Base):
    __tablename__ = "support_conversations"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "peer_id", name="uq_support_org_user_peer"),)

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
    peer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SupportChannel.CUSTOMER.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SupportConversationStatus.OPEN.value, index=True)
    context_type: Mapped[str] = mapped_column(String(20), nullable=False, default=SupportContextType.GENERAL.value, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    last_message_preview: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_sender_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    last_sender_is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    customer_last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    staff_last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    peer = relationship("User", foreign_keys=[peer_id], lazy="joined")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], lazy="joined")
    order = relationship("Order", lazy="joined")
    product = relationship("Product", lazy="joined")
    messages = relationship(
        "SupportMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="SupportMessage.created_at",
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("support_conversations.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    conversation = relationship("SupportConversation", back_populates="messages")
    sender = relationship("User", lazy="joined")
