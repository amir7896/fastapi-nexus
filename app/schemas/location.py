from pydantic import BaseModel, ConfigDict, Field


class LocationListResponse(BaseModel):
    message: str
    data: list[str] = Field(default_factory=list)


class PhoneCodeRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    country: str
    iso2: str
    dial_code: str = Field(serialization_alias="dialCode")
    flag: str = ""
    example: str = ""
    national_length: int = Field(default=0, serialization_alias="nationalLength")
    max_national_length: int = Field(default=0, serialization_alias="maxNationalLength")


class PhoneCodeListResponse(BaseModel):
    message: str
    data: list[PhoneCodeRead] = Field(default_factory=list)
