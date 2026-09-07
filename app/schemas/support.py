from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PaginatedResponse


class SupportContextType(str, Enum):
    GENERAL = "GENERAL"
    ORDER = "ORDER"
    PRODUCT = "PRODUCT"


class SupportConversationStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class SupportConversationCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    context_type: SupportContextType = Field(default=SupportContextType.GENERAL, alias="contextType")
    order_id: UUID | None = Field(default=None, alias="orderId")
    product_id: UUID | None = Field(default=None, alias="productId")
    subject: str | None = Field(default=None, max_length=160)
    message: str = Field(..., min_length=1, max_length=4000)


class SupportMessageCreateRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class SupportMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    conversation_id: UUID = Field(serialization_alias="conversationId")
    sender_id: UUID = Field(serialization_alias="senderId")
    sender_name: str = Field(serialization_alias="senderName")
    is_staff: bool = Field(serialization_alias="isStaff")
    body: str
    seen_at: datetime | None = Field(default=None, serialization_alias="seenAt")
    created_at: datetime = Field(serialization_alias="createdAt")


class SupportConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    user_id: UUID = Field(serialization_alias="userId")
    customer_name: str = Field(serialization_alias="customerName")
    customer_email: str | None = Field(default=None, serialization_alias="customerEmail")
    status: SupportConversationStatus
    context_type: SupportContextType = Field(serialization_alias="contextType")
    order_id: UUID | None = Field(default=None, serialization_alias="orderId")
    order_number: int | None = Field(default=None, serialization_alias="orderNumber")
    product_id: UUID | None = Field(default=None, serialization_alias="productId")
    product_name: str | None = Field(default=None, serialization_alias="productName")
    subject: str
    last_message_preview: str | None = Field(default=None, serialization_alias="lastMessagePreview")
    last_message_at: datetime | None = Field(default=None, serialization_alias="lastMessageAt")
    last_sender_is_staff: bool = Field(serialization_alias="lastSenderIsStaff")
    unread_count: int = Field(default=0, serialization_alias="unreadCount")
    peer_online: bool = Field(default=False, serialization_alias="peerOnline")
    chat_closed: bool = Field(default=False, serialization_alias="chatClosed")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class SupportConversationResponse(BaseModel):
    message: str
    conversation: SupportConversationRead


class SupportConversationListResponse(PaginatedResponse[SupportConversationRead]):
    pass


class SupportMessageResponse(BaseModel):
    message: str
    data: SupportMessageRead


class SupportMessageListResponse(PaginatedResponse[SupportMessageRead]):
    conversation: SupportConversationRead


class SupportUnreadResponse(BaseModel):
    message: str
    count: int


class SupportPresenceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    support_online: bool = Field(serialization_alias="supportOnline")
    online_user_ids: list[str] = Field(serialization_alias="onlineUserIds")
