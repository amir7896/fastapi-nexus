from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str = Field(examples=["Operation successful"])


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    environment: str = Field(examples=["development"])
    version: str = Field(examples=["0.1.0"])
