from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.security import hash_otp
from app.db.session import SessionLocal
from app.repositories.password_reset_repository import PasswordResetRepository
from tests.conftest import mark_email_verified


def _capture_reset_email(monkeypatch, captured: dict[str, str]) -> None:
    def fake_send(self, *, to_email: str, otp: str) -> None:
        captured["to_email"] = to_email
        captured["otp"] = otp

    monkeypatch.setattr(
        "app.services.email_service.EmailService.send_password_reset",
        fake_send,
    )


def _silence_verification_email(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.email_service.EmailService.send_email_verification",
        lambda self, *, to_email, otp: None,
    )


def test_forgot_password_returns_generic_message_for_unknown_email(client, api_prefix):
    response = client.post(
        f"{api_prefix}/auth/forgot-password",
        json={"email": f"missing-{uuid4().hex}@gmail.com"},
    )

    assert response.status_code == 200
    assert "password reset code" in response.json()["message"].lower()


def test_forgot_password_sends_otp_and_stores_hash(
    client,
    api_prefix,
    signup_payload,
    monkeypatch,
):
    _silence_verification_email(monkeypatch)
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    captured: dict[str, str] = {}
    _capture_reset_email(monkeypatch, captured)

    response = client.post(
        f"{api_prefix}/auth/forgot-password",
        json={"email": signup_payload["email"]},
    )

    assert response.status_code == 200
    assert "password reset code" in response.json()["message"].lower()
    assert captured["to_email"] == signup_payload["email"].lower()
    assert len(captured["otp"]) == 6

    token_hash = hash_otp(captured["otp"])
    db = SessionLocal()
    try:
        row = PasswordResetRepository(db).get_by_token_hash(token_hash)
        assert row is not None
        assert row.used_at is None
    finally:
        db.close()


def test_reset_password_with_otp(
    client,
    api_prefix,
    signup_payload,
    monkeypatch,
):
    _silence_verification_email(monkeypatch)
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    mark_email_verified(signup_payload["email"])

    captured: dict[str, str] = {}
    _capture_reset_email(monkeypatch, captured)

    forgot = client.post(
        f"{api_prefix}/auth/forgot-password",
        json={"email": signup_payload["email"]},
    )
    assert forgot.status_code == 200

    new_password = "NewSecret123"
    reset = client.post(
        f"{api_prefix}/auth/reset-password",
        json={
            "email": signup_payload["email"],
            "otp": captured["otp"],
            "newPassword": new_password,
        },
    )
    assert reset.status_code == 200
    assert "reset successfully" in reset.json()["message"].lower()

    old_login = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert old_login.status_code == 401

    new_login = client.post(
        f"{api_prefix}/auth/login",
        json={"email": signup_payload["email"], "password": new_password},
    )
    assert new_login.status_code == 200
    assert new_login.json()["access_token"]

    reuse = client.post(
        f"{api_prefix}/auth/reset-password",
        json={
            "email": signup_payload["email"],
            "otp": captured["otp"],
            "newPassword": "AnotherPass1",
        },
    )
    assert reuse.status_code == 400
    assert reuse.json()["detail"] == "Invalid or expired OTP"


def test_reset_password_rejects_wrong_otp(client, api_prefix, signup_payload, monkeypatch):
    _silence_verification_email(monkeypatch)
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    mark_email_verified(signup_payload["email"])

    captured: dict[str, str] = {}
    _capture_reset_email(monkeypatch, captured)
    client.post(
        f"{api_prefix}/auth/forgot-password",
        json={"email": signup_payload["email"]},
    )

    response = client.post(
        f"{api_prefix}/auth/reset-password",
        json={
            "email": signup_payload["email"],
            "otp": "000000",
            "newPassword": "NewSecret123",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OTP"


def test_password_reset_otp_rejects_expired(
    client,
    api_prefix,
    signup_payload,
    monkeypatch,
):
    _silence_verification_email(monkeypatch)
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    captured: dict[str, str] = {}
    _capture_reset_email(monkeypatch, captured)

    client.post(
        f"{api_prefix}/auth/forgot-password",
        json={"email": signup_payload["email"]},
    )
    token_hash = hash_otp(captured["otp"])

    db = SessionLocal()
    try:
        row = PasswordResetRepository(db).get_by_token_hash(token_hash)
        assert row is not None
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"{api_prefix}/auth/reset-password",
        json={
            "email": signup_payload["email"],
            "otp": captured["otp"],
            "newPassword": "NewSecret123",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OTP"
