from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.pagination import PaginatedResponse


class BrandCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=100, examples=["Nike"])
    is_active: bool = Field(default=True, alias="isActive")


class BrandUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=2, max_length=100, examples=["Nike"])
    is_active: bool | None = Field(default=None, alias="isActive")

    @model_validator(mode="after")
    def require_one_field(self):
        if self.name is None and self.is_active is None:
            raise ValueError("Provide name or isActive")
        return self


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    deleted_at: datetime | None = Field(default=None, serialization_alias="deletedAt")


class BrandListResponse(PaginatedResponse[BrandRead]):
    """Paginated brands list using the shared pagination response shape."""


class BrandResponse(BaseModel):
    message: str
    brand: BrandRead
