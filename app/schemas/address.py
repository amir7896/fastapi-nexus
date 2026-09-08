from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.shipping import ShippingAddressRequest


class SavedAddressCreateRequest(ShippingAddressRequest):
    label: str | None = Field(default=None, max_length=40, examples=["Home"])
    is_default: bool = Field(default=False, alias="isDefault")


class SavedAddressUpdateRequest(ShippingAddressRequest):
    label: str | None = Field(default=None, max_length=40, examples=["Work"])
    is_default: bool = Field(default=False, alias="isDefault")


class SavedAddressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    label: str | None = None
    name: str
    phone_country_code: str = Field(serialization_alias="phoneCountryCode")
    phone: str
    address: str
    city: str
    state: str
    country: str
    is_default: bool = Field(serialization_alias="isDefault")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class SavedAddressListResponse(BaseModel):
    message: str
    data: list[SavedAddressRead]


class SavedAddressResponse(BaseModel):
    message: str
    address: SavedAddressRead
