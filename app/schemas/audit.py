from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PaginatedResponse


class StaffAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    actor_id: UUID | None = Field(default=None, serialization_alias="actorId")
    actor_name: str = Field(serialization_alias="actorName")
    actor_email: str = Field(serialization_alias="actorEmail")
    action: str
    target_type: str = Field(serialization_alias="targetType")
    target_id: str | None = Field(default=None, serialization_alias="targetId")
    summary: str
    extra: dict | None = None
    created_at: datetime = Field(serialization_alias="createdAt")


class StaffAuditLogListResponse(PaginatedResponse[StaffAuditLogRead]):
    pass
