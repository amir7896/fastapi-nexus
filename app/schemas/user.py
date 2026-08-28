from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field  # pyright: ignore[reportMissingImports]

from app.models.user import UserRole
from app.schemas.pagination import PaginatedResponse


class UserRead(BaseModel):
    """Public representation of a user. Never exposes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(examples=["550e8400-e29b-41d4-a716-446655440000"])
    name: str = Field(examples=["Amir"])
    email: EmailStr = Field(examples=["amir@gmail.com"])
    age: int | None = Field(default=None, examples=[25])
    role: UserRole = Field(examples=[UserRole.USER])
    created_at: datetime


class UserUpdateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, examples=["Amir"])
    age: int | None = Field(default=None, ge=1, le=150, examples=[25])


class UserResponse(BaseModel):
    message: str
    user: UserRead


class UserListResponse(PaginatedResponse[UserRead]):
    """Paginated users list using the shared pagination response shape."""
