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
    VerifyEmailRequest,
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
    summary="Request a password reset email",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    return auth_service.forgot_password(payload)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with a one-time token",
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
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email with a one-time token",
)
def verify_email(
    payload: VerifyEmailRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    return auth_service.verify_email(payload)


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend email verification link",
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
