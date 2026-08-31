import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError
from app.core.logging import get_logger

logger = get_logger(__name__)

_RESEND_EMAILS_URL = "https://api.resend.com/emails"


class EmailService:
    """Transactional email via Resend HTTP API (logs links when API key is unset)."""

    def send_password_reset(self, *, to_email: str, reset_url: str) -> None:
        settings = get_settings()
        subject = f"Reset your {settings.PROJECT_NAME} password"
        html = self._password_reset_html(settings=settings, reset_url=reset_url)
        text = (
            f"Reset your {settings.PROJECT_NAME} password using this link "
            f"(expires soon):\n\n{reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        )
        self._send(
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
            log_label="password reset",
            failure_message="Unable to send password reset email right now",
            reset_url_for_dev=reset_url,
        )

    def send_email_verification(self, *, to_email: str, verify_url: str) -> None:
        settings = get_settings()
        subject = f"Verify your {settings.PROJECT_NAME} email"
        html = self._email_verification_html(settings=settings, verify_url=verify_url)
        text = (
            f"Verify your {settings.PROJECT_NAME} email using this link "
            f"(expires soon):\n\n{verify_url}\n\n"
            "If you did not create an account, you can ignore this email."
        )
        self._send(
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
            log_label="email verification",
            failure_message="Unable to send verification email right now",
            reset_url_for_dev=verify_url,
        )

    def _send(
        self,
        *,
        to_email: str,
        subject: str,
        html: str,
        text: str,
        log_label: str,
        failure_message: str,
        reset_url_for_dev: str,
    ) -> None:
        settings = get_settings()

        if not settings.resend_enabled:
            logger.warning(
                "RESEND_API_KEY not set — %s email for %s (dev log only): %s",
                log_label,
                to_email,
                reset_url_for_dev,
            )
            return

        try:
            response = httpx.post(
                _RESEND_EMAILS_URL,
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": [to_email],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
                timeout=15.0,
            )
            if response.is_error:
                logger.error(
                    "Resend rejected %s email to %s: %s %s",
                    log_label,
                    to_email,
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Failed to send %s email to %s", log_label, to_email)
            raise BadRequestError(failure_message) from exc

        logger.info("Sent %s email to %s", log_label, to_email)

    @staticmethod
    def _password_reset_html(*, settings: Settings, reset_url: str) -> str:
        return f"""\
<!DOCTYPE html>
<html>
  <body style="font-family: sans-serif; line-height: 1.5; color: #111;">
    <h2>Reset your password</h2>
    <p>We received a request to reset your {settings.PROJECT_NAME} password.</p>
    <p>
      <a href="{reset_url}" style="display: inline-block; padding: 10px 16px;
         background: #2563eb; color: #fff; text-decoration: none; border-radius: 6px;">
        Reset password
      </a>
    </p>
    <p>Or copy this link into your browser:</p>
    <p style="word-break: break-all;">{reset_url}</p>
    <p>This link expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.
       If you did not request a reset, you can ignore this email.</p>
  </body>
</html>
"""

    @staticmethod
    def _email_verification_html(*, settings: Settings, verify_url: str) -> str:
        return f"""\
<!DOCTYPE html>
<html>
  <body style="font-family: sans-serif; line-height: 1.5; color: #111;">
    <h2>Verify your email</h2>
    <p>Thanks for signing up for {settings.PROJECT_NAME}. Confirm your email to activate your account.</p>
    <p>
      <a href="{verify_url}" style="display: inline-block; padding: 10px 16px;
         background: #2563eb; color: #fff; text-decoration: none; border-radius: 6px;">
        Verify email
      </a>
    </p>
    <p>Or copy this link into your browser:</p>
    <p style="word-break: break-all;">{verify_url}</p>
    <p>This link expires in {settings.EMAIL_VERIFICATION_EXPIRE_MINUTES} minutes.
       If you did not create an account, you can ignore this email.</p>
  </body>
</html>
"""
