from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import MessageResponse


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    title: str
    description: str
    type: str
    order_id: UUID | None = Field(default=None, alias="orderId")
    product_id: UUID | None = Field(default=None, alias="productId")
    conversation_id: UUID | None = Field(default=None, alias="conversationId")
    is_read: bool = Field(alias="isRead")
    created_at: datetime = Field(alias="createdAt")


class NotificationListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    data: list[NotificationRead]
    unread_count: int = Field(alias="unreadCount")


class NotificationResponse(MessageResponse):
    notification: NotificationRead
