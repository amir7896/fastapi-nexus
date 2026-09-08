from pydantic import BaseModel, ConfigDict, Field


class ShippingAddressRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=80, examples=["Amir Shahzad"])
    phone_country_code: str = Field(
        ...,
        min_length=2,
        max_length=8,
        alias="phoneCountryCode",
        examples=["+92"],
    )
    phone: str = Field(..., min_length=4, max_length=30, examples=["3001234567"])
    address: str = Field(..., min_length=5, max_length=255, examples=["12 Market Street"])
    city: str = Field(..., min_length=2, max_length=80, examples=["Lahore"])
    state: str = Field(..., min_length=1, max_length=80, examples=["Punjab"])
    country: str = Field(..., min_length=2, max_length=80, examples=["Pakistan"])


class ShippingAddressRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    phone_country_code: str = Field(default="", serialization_alias="phoneCountryCode")
    phone: str
    address: str
    city: str
    state: str = ""
    country: str
