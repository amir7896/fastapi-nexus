import html as html_lib

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError
from app.core.logging import get_logger

logger = get_logger(__name__)

_RESEND_EMAILS_URL = "https://api.resend.com/emails"


class EmailService:
    """Transactional email via Resend HTTP API (logs OTP when API key is unset)."""

    def send_password_reset(self, *, to_email: str, otp: str) -> None:
        settings = get_settings()
        subject = f"Your {settings.PROJECT_NAME} password reset code"
        html = self._otp_email_html(
            settings=settings,
            eyebrow="Password reset",
            headline="Reset your password",
            intro=(
                f"Use the one-time code below to reset your {settings.PROJECT_NAME} "
                "password. Enter it in the app — do not share this code with anyone."
            ),
            otp=otp,
            expire_minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES,
            footer_note="If you did not request a password reset, you can ignore this email.",
        )
        text = (
            f"Your {settings.PROJECT_NAME} password reset code is: {otp}\n\n"
            f"This code expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.\n"
            "If you did not request this, you can ignore this email."
        )
        self._send(
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
            log_label="password reset",
            failure_message="Unable to send password reset email right now",
            otp_for_dev=otp,
        )

    def send_email_verification(self, *, to_email: str, otp: str) -> None:
        settings = get_settings()
        subject = f"Your {settings.PROJECT_NAME} verification code"
        html = self._otp_email_html(
            settings=settings,
            eyebrow="Email verification",
            headline="Verify your email",
            intro=(
                f"Welcome to {settings.PROJECT_NAME}. Enter this one-time code to "
                "confirm your email address and activate your account."
            ),
            otp=otp,
            expire_minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES,
            footer_note="If you did not create an account, you can ignore this email.",
        )
        text = (
            f"Your {settings.PROJECT_NAME} verification code is: {otp}\n\n"
            f"This code expires in {settings.EMAIL_VERIFICATION_EXPIRE_MINUTES} minutes.\n"
            "If you did not create an account, you can ignore this email."
        )
        self._send(
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
            log_label="email verification",
            failure_message="Unable to send verification email right now",
            otp_for_dev=otp,
        )

    def send_order_notice(
        self,
        *,
        to_email: str,
        subject: str,
        headline: str,
        intro: str,
        order_number: int,
        extra: str = "",
        action_url: str | None = None,
    ) -> None:
        settings = get_settings()
        html = self._notice_email_html(
            settings=settings,
            headline=headline,
            intro=intro,
            order_number=order_number,
            extra=extra,
            action_url=action_url,
        )
        text = (
            f"{headline}\n\n{intro}\n\nOrder #{order_number}\n"
            + (f"{extra}\n" if extra else "")
            + (f"\nView order: {action_url}\n" if action_url else "")
        )
        self._send(
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
            log_label="order notice",
            failure_message="Unable to send order email right now",
            otp_for_dev=f"#{order_number}",
            raise_on_error=False,
        )

    def send_staff_notice(
        self,
        *,
        to_email: str,
        subject: str,
        headline: str,
        intro: str,
    ) -> None:
        settings = get_settings()
        html = self._wrap_email(
            title=headline,
            eyebrow="Staff alert",
            body=(
                f'<h1 style="margin:0 0 12px;font-size:24px;line-height:1.3;font-weight:700;color:#0f172a;">'
                f"{html_lib.escape(headline)}</h1>"
                f'<p style="margin:0;font-size:15px;line-height:1.6;color:#475569;">{html_lib.escape(intro)}</p>'
            ),
            footer_note="You received this because you are on the catalog or fulfillment team.",
            settings=settings,
        )
        self._send(
            to_email=to_email,
            subject=subject,
            html=html,
            text=f"{headline}\n\n{intro}\n",
            log_label="staff notice",
            failure_message="Unable to send staff alert right now",
            otp_for_dev=headline,
            raise_on_error=False,
        )

    def send_staff_invite(
        self,
        *,
        to_email: str,
        organization_name: str,
        role: str,
        accept_url: str,
        inviter_name: str,
    ) -> None:
        settings = get_settings()
        subject = f"Join {organization_name} on {settings.PROJECT_NAME}"
        intro = (
            f"{inviter_name} invited you to join {organization_name} as {role}. "
            "Open the link below to accept."
        )
        html = self._wrap_email(
            title="You're invited",
            eyebrow="Team invite",
            body=(
                '<h1 style="margin:0 0 12px;font-size:24px;line-height:1.3;font-weight:700;color:#0f172a;">'
                "Join your team</h1>"
                f'<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#475569;">{html_lib.escape(intro)}</p>'
                f'<p style="margin:28px 0 0;"><a href="{html_lib.escape(accept_url)}" '
                'style="display:inline-block;background:#2065d1;color:#ffffff;text-decoration:none;'
                'font-weight:700;border-radius:10px;padding:12px 18px;">Accept invite</a></p>'
            ),
            footer_note="If you were not expecting this, you can ignore the email.",
            settings=settings,
        )
        self._send(
            to_email=to_email,
            subject=subject,
            html=html,
            text=f"{intro}\n\nAccept: {accept_url}\n",
            log_label="staff invite",
            failure_message="Unable to send invite email right now",
            otp_for_dev=accept_url,
            raise_on_error=False,
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
        otp_for_dev: str,
        raise_on_error: bool = True,
    ) -> None:
        settings = get_settings()

        if not settings.resend_enabled:
            logger.warning(
                "RESEND_API_KEY not set — %s email for %s (dev log only): OTP=%s",
                log_label,
                to_email,
                otp_for_dev,
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
            if raise_on_error:
                raise BadRequestError(failure_message) from exc
            return

        logger.info("Sent %s email to %s", log_label, to_email)

    @staticmethod
    def _otp_email_html(
        *,
        settings: Settings,
        eyebrow: str,
        headline: str,
        intro: str,
        otp: str,
        expire_minutes: int,
        footer_note: str,
    ) -> str:
        otp_display = " ".join(html_lib.escape(otp))
        body = f"""
              <h1 style="margin:0 0 12px;font-size:24px;line-height:1.3;font-weight:700;color:#0f172a;">{html_lib.escape(headline)}</h1>
              <p style="margin:0 0 28px;font-size:15px;line-height:1.6;color:#475569;">{html_lib.escape(intro)}</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:22px 16px;">
                    <p style="margin:0 0 8px;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:#64748b;font-weight:600;">One-time code</p>
                    <p style="margin:0;font-size:36px;line-height:1.2;letter-spacing:0.28em;font-weight:700;color:#0f172a;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;">{otp_display}</p>
                  </td>
                </tr>
              </table>
              <p style="margin:24px 0 0;font-size:14px;line-height:1.6;color:#64748b;">
                This code expires in <strong style="color:#0f172a;">{expire_minutes} minutes</strong>.
                For your security, never share it with anyone.
              </p>
"""
        return EmailService._wrap_email(
            title=headline,
            eyebrow=eyebrow,
            body=body,
            footer_note=footer_note,
            settings=settings,
        )

    @staticmethod
    def _notice_email_html(
        *,
        settings: Settings,
        headline: str,
        intro: str,
        order_number: int,
        extra: str,
        action_url: str | None,
    ) -> str:
        extra_html = (
            f'<p style="margin:16px 0 0;font-size:14px;line-height:1.6;color:#475569;">{html_lib.escape(extra)}</p>'
            if extra
            else ""
        )
        button = (
            f'<p style="margin:28px 0 0;"><a href="{html_lib.escape(action_url)}" '
            'style="display:inline-block;background:#2065d1;color:#ffffff;text-decoration:none;'
            'font-weight:700;border-radius:10px;padding:12px 18px;">View order</a></p>'
            if action_url
            else ""
        )
        body = f"""
              <h1 style="margin:0 0 12px;font-size:24px;line-height:1.3;font-weight:700;color:#0f172a;">{html_lib.escape(headline)}</h1>
              <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#475569;">{html_lib.escape(intro)}</p>
              <p style="margin:0;font-size:14px;font-weight:700;">Order #{order_number}</p>
              {extra_html}
              {button}
"""
        return EmailService._wrap_email(
            title=headline,
            eyebrow="Order update",
            body=body,
            footer_note="You received this because you placed an order.",
            settings=settings,
        )

    @staticmethod
    def _wrap_email(
        *,
        title: str,
        eyebrow: str,
        body: str,
        footer_note: str,
        settings: Settings,
    ) -> str:
        brand = html_lib.escape(settings.PROJECT_NAME)
        return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html_lib.escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6f8;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 8px 24px rgba(15,23,42,0.06);">
          <tr>
            <td style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);padding:28px 32px;">
              <p style="margin:0;font-size:13px;letter-spacing:0.08em;text-transform:uppercase;color:#94a3b8;font-weight:600;">{brand}</p>
              <p style="margin:8px 0 0;font-size:12px;color:#cbd5e1;">{html_lib.escape(eyebrow)}</p>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              {body}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px 28px;border-top:1px solid #e2e8f0;background:#fafbfc;">
              <p style="margin:0;font-size:12px;line-height:1.6;color:#94a3b8;">{html_lib.escape(footer_note)}</p>
              <p style="margin:10px 0 0;font-size:12px;color:#cbd5e1;">&copy; {brand}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
