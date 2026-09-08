from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserRead


class SignupRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

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
    store_name: str | None = Field(
        default=None,
        alias="storeName",
        min_length=2,
        max_length=80,
        examples=["Northwind"],
    )
    store_slug: str | None = Field(
        default=None,
        alias="storeSlug",
        min_length=2,
        max_length=80,
        examples=["nexus"],
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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        examples=["amir@gmail.com"],
    )


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "email": "amir@gmail.com",
                    "otp": "829301",
                    "newPassword": "NewSecret123",
                }
            ]
        },
    )

    email: EmailStr = Field(..., examples=["amir@gmail.com"])
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        examples=["829301"],
        description="6-digit OTP from the forgot-password email",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        alias="newPassword",
        examples=["NewSecret123"],
    )


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    current_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        alias="currentPassword",
        examples=["Secret123"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        alias="newPassword",
        examples=["NewSecret123"],
    )


class VerifyOtpRequest(BaseModel):
    """Verify the 6-digit OTP sent after signup / resend-verification."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "email": "amir@gmail.com",
                    "otp": "414912",
                }
            ]
        },
    )

    email: EmailStr = Field(..., examples=["amir@gmail.com"])
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        examples=["414912"],
        description="6-digit one-time code from the verification email",
    )


class VerifyOtpResponse(BaseModel):
    message: str = Field(examples=["Email verified successfully"])


class ResendVerificationRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        examples=["amir@gmail.com"],
    )
