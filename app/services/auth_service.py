from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.user_repository import UserRepository
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
from app.services.email_service import EmailService

logger = get_logger(__name__)

_FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for that email, a password reset code has been sent."
)
_RESEND_VERIFICATION_MESSAGE = (
    "If an unverified account exists for that email, a verification code has been sent."
)
_EMAIL_NOT_VERIFIED_MESSAGE = "Please verify your email before logging in"
_INVALID_OTP_MESSAGE = "Invalid or expired OTP"


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        password_resets: PasswordResetRepository,
        email_verifications: EmailVerificationRepository,
        emails: EmailService,
    ) -> None:
        self._users = users
        self._password_resets = password_resets
        self._email_verifications = email_verifications
        self._emails = emails

    def signup(self, payload: SignupRequest) -> AuthResponse:
        if self._users.exists(payload.email):
            raise ConflictError("Email already exists")

        user = self._users.create(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            age=payload.age,
            role=UserRole.USER,
            email_verified=False,
        )
        self._issue_email_verification(user)
        logger.info("Registered user %s", user.email)

        return AuthResponse(
            message="Signup successful. Please check your email for the verification code.",
            user=UserRead.model_validate(user),
        )

    def login(self, payload: LoginRequest) -> AuthResponse:
        user = self._authenticate(payload)
        self._ensure_email_verified(user)
        return self._auth_response("Login successful", user)

    def admin_login(self, payload: LoginRequest) -> AuthResponse:
        user = self._authenticate(payload)
        self._ensure_email_verified(user)
        if not user.is_staff:
            raise ForbiddenError("Staff access required")

        return self._auth_response("Staff login successful", user)

    def forgot_password(self, payload: ForgotPasswordRequest) -> MessageResponse:
        user = self._users.get_by_email(payload.email)
        if user is None:
            return MessageResponse(message=_FORGOT_PASSWORD_MESSAGE)

        settings = get_settings()
        otp = generate_otp()
        token_hash = hash_otp(otp)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )

        self._password_resets.invalidate_unused_for_user(user.id)
        self._password_resets.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        self._emails.send_password_reset(to_email=user.email, otp=otp)
        logger.info("Created password reset OTP for user %s", user.email)

        return MessageResponse(message=_FORGOT_PASSWORD_MESSAGE)

    def reset_password(self, payload: ResetPasswordRequest) -> MessageResponse:
        user = self._users.get_by_email(payload.email)
        if user is None:
            raise BadRequestError(_INVALID_OTP_MESSAGE)

        row = self._password_resets.get_by_token_hash(hash_otp(payload.otp))
        if row is None or row.used_at is not None or row.user_id != user.id:
            raise BadRequestError(_INVALID_OTP_MESSAGE)

        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise BadRequestError(_INVALID_OTP_MESSAGE)

        self._users.update_password(user, password_hash=hash_password(payload.new_password))
        self._password_resets.mark_used(row)
        self._password_resets.invalidate_unused_for_user(user.id)
        logger.info("Password reset completed for user %s", user.email)

        return MessageResponse(message="Password has been reset successfully")

    def change_password(
        self,
        payload: ChangePasswordRequest,
        *,
        current_user: User,
    ) -> MessageResponse:
        if not verify_password(payload.current_password, current_user.password_hash):
            raise UnauthorizedError("Current password is incorrect")

        if payload.current_password == payload.new_password:
            raise BadRequestError("New password must be different from the current password")

        self._users.update_password(
            current_user,
            password_hash=hash_password(payload.new_password),
        )
        self._password_resets.invalidate_unused_for_user(current_user.id)
        logger.info("Password changed for user %s", current_user.email)

        return MessageResponse(message="Password has been changed successfully")

    def verify_otp(self, payload: VerifyOtpRequest) -> VerifyOtpResponse:
        user = self._users.get_by_email(payload.email)
        if user is None:
            raise BadRequestError(_INVALID_OTP_MESSAGE)
        return self._verify_email_otp(user, payload.otp)

    def resend_verification(self, payload: ResendVerificationRequest) -> MessageResponse:
        user = self._users.get_by_email(payload.email)
        if user is None or user.email_verified:
            return MessageResponse(message=_RESEND_VERIFICATION_MESSAGE)

        self._issue_email_verification(user)
        return MessageResponse(message=_RESEND_VERIFICATION_MESSAGE)

    def _verify_email_otp(self, user: User, otp: str) -> VerifyOtpResponse:
        row = self._email_verifications.get_by_token_hash(hash_otp(otp))
        if row is None or row.used_at is not None or row.user_id != user.id:
            raise BadRequestError(_INVALID_OTP_MESSAGE)

        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise BadRequestError(_INVALID_OTP_MESSAGE)

        if user.email_verified:
            self._email_verifications.mark_used(row)
            return VerifyOtpResponse(message="Email is already verified")

        self._users.mark_email_verified(user)
        self._email_verifications.mark_used(row)
        self._email_verifications.invalidate_unused_for_user(user.id)
        logger.info("Email verified via OTP for user %s", user.email)

        return VerifyOtpResponse(message="Email verified successfully")

    def _issue_email_verification(self, user: User) -> None:
        settings = get_settings()
        otp = generate_otp()
        token_hash = hash_otp(otp)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES
        )

        self._email_verifications.invalidate_unused_for_user(user.id)
        self._email_verifications.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        self._emails.send_email_verification(to_email=user.email, otp=otp)
        logger.info("Created email verification OTP for user %s", user.email)

    def _ensure_email_verified(self, user: User) -> None:
        settings = get_settings()
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.email_verified:
            raise ForbiddenError(_EMAIL_NOT_VERIFIED_MESSAGE)

    def _authenticate(self, payload: LoginRequest) -> User:
        user = self._users.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        return user

    def _auth_response(self, message: str, user: User) -> AuthResponse:
        token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value,
        )
        return AuthResponse(
            message=message,
            user=UserRead.model_validate(user),
            access_token=token,
            token_type="bearer",
        )
