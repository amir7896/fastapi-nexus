from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.coupon import CouponType


class CouponCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(..., min_length=3, max_length=40)
    type: CouponType = CouponType.PERCENT
    value: Decimal = Field(..., gt=0)
    min_subtotal: Decimal | None = Field(default=None, alias="minSubtotal", ge=0)
    max_uses: int | None = Field(default=None, alias="maxUses", ge=1)
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    is_active: bool = Field(default=True, alias="isActive")


class CouponUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: CouponType | None = None
    value: Decimal | None = Field(default=None, gt=0)
    min_subtotal: Decimal | None = Field(default=None, alias="minSubtotal", ge=0)
    max_uses: int | None = Field(default=None, alias="maxUses", ge=1)
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    is_active: bool | None = Field(default=None, alias="isActive")


class CouponRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    code: str
    type: str
    value: Decimal
    min_subtotal: Decimal | None = Field(default=None, alias="minSubtotal")
    max_uses: int | None = Field(default=None, alias="maxUses")
    used_count: int = Field(alias="usedCount")
    is_active: bool = Field(alias="isActive")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    created_at: datetime = Field(alias="createdAt")


class CouponListResponse(BaseModel):
    message: str
    data: list[CouponRead]


class CouponResponse(BaseModel):
    message: str
    coupon: CouponRead


class CouponPreviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    code: str
    type: str
    value: Decimal
    discount: Decimal
    min_subtotal: Decimal | None = Field(default=None, alias="minSubtotal")
