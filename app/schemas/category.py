from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PaginatedResponse


class CategoryCreateRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Electronics"],
    )


class CategoryUpdateRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Electronics"],
    )


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    deleted_at: datetime | None = Field(
        default=None,
        serialization_alias="deletedAt",
    )


class CategoryListResponse(PaginatedResponse[CategoryRead]):
    """Paginated categories list using the shared pagination response shape."""


class CategoryResponse(BaseModel):
    message: str
    category: CategoryRead
