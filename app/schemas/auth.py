from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class SignupRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        examples=["Amir"],
    )

    email: EmailStr = Field(
        ...,
        examples=["amir@gmail.com"],
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        examples=["Secret123"],
    )

    age: int | None = Field(
        default=None,
        ge=18,
        le=100,
        examples=[25],
    )


class LoginRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        examples=["amir@gmail.com"],
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        examples=["Secret123"],
    )


class AuthResponse(BaseModel):
    message: str = Field(examples=["Login successful"])
    user: UserRead
    access_token: str | None = Field(default=None, examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field(default="bearer", examples=["bearer"])
