from pydantic import BaseModel, ConfigDict, Field


class ShippingAddressRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=80, examples=["Amir Shahzad"])
    phone: str = Field(..., min_length=6, max_length=30, examples=["03012345678"])
    address: str = Field(..., min_length=5, max_length=255, examples=["12 Market Street"])
    city: str = Field(..., min_length=2, max_length=80, examples=["Lahore"])
    country: str = Field(..., min_length=2, max_length=80, examples=["Pakistan"])


class ShippingAddressRead(BaseModel):
    name: str
    phone: str
    address: str
    city: str
    country: str
