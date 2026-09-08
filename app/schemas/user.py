from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field  # pyright: ignore[reportMissingImports]

from app.models.user import UserRole
from app.schemas.pagination import PaginatedResponse


class UserRead(BaseModel):
    """Public representation of a user. Never exposes the password hash."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(examples=["550e8400-e29b-41d4-a716-446655440000"])
    name: str = Field(examples=["Amir"])
    email: EmailStr = Field(examples=["amir@gmail.com"])
    age: int | None = Field(default=None, examples=[25])
    role: UserRole = Field(examples=[UserRole.USER])
    email_verified: bool = Field(serialization_alias="emailVerified", examples=[True])
    notify_order_email: bool = Field(default=True, serialization_alias="notifyOrderEmail")
    notify_support_email: bool = Field(default=True, serialization_alias="notifySupportEmail")
    notify_marketing_email: bool = Field(default=False, serialization_alias="notifyMarketingEmail")
    organization_id: UUID | None = Field(default=None, serialization_alias="organizationId")
    organization_name: str | None = Field(default=None, serialization_alias="organizationName")
    organization_slug: str | None = Field(default=None, serialization_alias="organizationSlug")
    organization_plan: str | None = Field(default=None, serialization_alias="organizationPlan")
    organization_logo_url: str | None = Field(default=None, serialization_alias="organizationLogoUrl")
    created_at: datetime

    @classmethod
    def from_user(cls, user, organization=None) -> "UserRead":
        org = organization
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            age=user.age,
            role=user.role,
            email_verified=user.email_verified,
            notify_order_email=getattr(user, "notify_order_email", True),
            notify_support_email=getattr(user, "notify_support_email", True),
            notify_marketing_email=getattr(user, "notify_marketing_email", False),
            organization_id=None if org is None else org.id,
            organization_name=None if org is None else org.name,
            organization_slug=None if org is None else org.slug,
            organization_plan=None if org is None else org.plan,
            organization_logo_url=None if org is None else org.logo_url,
            created_at=user.created_at,
        )



class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=50, examples=["Amir"])
    age: int | None = Field(default=None, ge=1, le=150, examples=[25])
    role: UserRole | None = Field(default=None, examples=[UserRole.MANAGER])
    email_verified: bool | None = Field(default=None, alias="emailVerified", examples=[True])
    notify_order_email: bool | None = Field(default=None, alias="notifyOrderEmail")
    notify_support_email: bool | None = Field(default=None, alias="notifySupportEmail")
    notify_marketing_email: bool | None = Field(default=None, alias="notifyMarketingEmail")


class UserResponse(BaseModel):
    message: str
    user: UserRead


class UserListResponse(PaginatedResponse[UserRead]):
    """Paginated users list using the shared pagination response shape."""
