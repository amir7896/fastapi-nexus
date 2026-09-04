from fastapi import APIRouter, status  # pyright: ignore[reportMissingImports]

from app.api.deps import AuthServiceDep, CurrentUserDep
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def signup(payload: SignupRequest, auth_service: AuthServiceDep) -> AuthResponse:
    return auth_service.signup(payload)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate an existing user",
)
def login(payload: LoginRequest, auth_service: AuthServiceDep) -> AuthResponse:
    return auth_service.login(payload)


@router.post(
    "/admin/login",
    response_model=AuthResponse,
    summary="Authenticate an admin user",
)
def admin_login(payload: LoginRequest, auth_service: AuthServiceDep) -> AuthResponse:
    return auth_service.admin_login(payload)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset OTP email",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    return auth_service.forgot_password(payload)


@router.post(
    "/verify-otp",
    response_model=VerifyOtpResponse,
    summary="Verify signup email OTP",
    description=(
        "Confirm the 6-digit code sent after signup or resend-verification.\n\n"
        "Example:\n"
        '`{"email":"amir@gmail.com","otp":"414912"}`\n\n'
        "For password reset, send the OTP directly to `/auth/reset-password` "
        "with `newPassword` (no purpose / resetToken needed)."
    ),
)
def verify_otp(
    payload: VerifyOtpRequest,
    auth_service: AuthServiceDep,
) -> VerifyOtpResponse:
    return auth_service.verify_otp(payload)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with email OTP",
    description=(
        "After forgot-password, pass the email OTP and new password here.\n\n"
        "Example:\n"
        '`{"email":"amir@gmail.com","otp":"829301","newPassword":"NewSecret123"}`'
    ),
)
def reset_password(
    payload: ResetPasswordRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    return auth_service.reset_password(payload)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password for the authenticated user",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    return auth_service.change_password(payload, current_user=current_user)


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend email verification OTP",
)
def resend_verification(
    payload: ResendVerificationRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    return auth_service.resend_verification(payload)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the currently authenticated user",
)
def me(current_user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(current_user)
