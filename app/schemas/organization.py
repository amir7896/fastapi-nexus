from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.schemas.pagination import PaginatedResponse


class MembershipRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    organization_id: UUID = Field(alias="organizationId")
    organization_slug: str = Field(alias="organizationSlug")
    organization_name: str = Field(alias="organizationName")
    logo_url: str | None = Field(default=None, alias="logoUrl")
    role: UserRole
    plan: str


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    slug: str
    logo_url: str | None = Field(default=None, alias="logoUrl")
    currency: str
    timezone: str
    tax_rate: Decimal = Field(alias="taxRate")
    shipping_flat_rate: Decimal = Field(alias="shippingFlatRate")
    notify_orders: bool = Field(alias="notifyOrders")
    notify_low_stock: bool = Field(alias="notifyLowStock")
    shop_url: str | None = Field(default=None, alias="shopUrl")
    plan: str
    plan_status: str = Field(alias="planStatus")
    created_at: datetime
    updated_at: datetime


class OrganizationResponse(BaseModel):
    message: str
    organization: OrganizationRead


class OrganizationCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=80)
    slug: str | None = Field(default=None, min_length=2, max_length=80)


class OrganizationUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=80)
    currency: str = Field(default="usd", min_length=3, max_length=3)
    timezone: str = Field(default="UTC", max_length=60)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, alias="taxRate")
    shipping_flat_rate: Decimal = Field(default=Decimal("0"), ge=0, alias="shippingFlatRate")
    notify_orders: bool = Field(default=True, alias="notifyOrders")
    notify_low_stock: bool = Field(default=True, alias="notifyLowStock")
    shop_url: str | None = Field(default=None, alias="shopUrl", max_length=255)


class SwitchOrganizationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    organization_id: UUID = Field(alias="organizationId")


class InviteCreateRequest(BaseModel):
    email: EmailStr
    role: UserRole = Field(examples=[UserRole.MANAGER])


class InviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    email: EmailStr
    role: UserRole
    organization_name: str = Field(alias="organizationName")
    expires_at: datetime = Field(alias="expiresAt")
    created_at: datetime


class InvitePreview(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    email: EmailStr
    role: UserRole
    organization_name: str = Field(alias="organizationName")
    needs_account: bool = Field(alias="needsAccount")


class InviteAcceptRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    token: str = Field(..., min_length=16)
    name: str | None = Field(default=None, min_length=2, max_length=50)
    password: str | None = Field(default=None, min_length=8, max_length=72)


class InviteListResponse(BaseModel):
    message: str
    data: list[InviteRead]


class MembershipListResponse(PaginatedResponse[MembershipRead]):
    pass


class TeamMemberRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    user_id: UUID = Field(alias="userId")
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool = Field(alias="isActive")
    created_at: datetime


class TeamMemberUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    role: UserRole | None = None
    is_active: bool | None = Field(default=None, alias="isActive")


class PublicStoreRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    slug: str
    logo_url: str | None = Field(default=None, alias="logoUrl")


class PublicStoreResponse(BaseModel):
    message: str
    store: PublicStoreRead


class TeamResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    members: list[TeamMemberRead]
    invites: list[InviteRead]
    seats_used: int = Field(alias="seatsUsed")
    seat_limit: int = Field(alias="seatLimit")


class PlanRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    seats: int
    products: int
    description: str
    current: bool
    price_configured: bool = Field(alias="priceConfigured")


class BillingInvoiceRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    number: str | None = None
    amount: str
    currency: str
    status: str | None = None
    hosted_invoice_url: str | None = Field(default=None, alias="hostedInvoiceUrl")
    created: int | None = None


class BillingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    plan: str
    plan_status: str = Field(alias="planStatus")
    plans: list[PlanRead]
    invoices: list[BillingInvoiceRead]
    portal_available: bool = Field(alias="portalAvailable")


class BillingCheckoutRequest(BaseModel):
    plan: str = Field(examples=["pro"])


class BillingCheckoutResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    checkout_url: str = Field(alias="checkoutUrl")


class BillingPortalResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    portal_url: str = Field(alias="portalUrl")
