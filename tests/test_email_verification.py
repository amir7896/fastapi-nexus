from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.security import hash_otp
from app.db.session import SessionLocal
from app.repositories.email_verification_repository import EmailVerificationRepository


def _capture_verification_email(monkeypatch, captured: dict[str, str]) -> None:
    def fake_send(self, *, to_email: str, otp: str) -> None:
        captured["to_email"] = to_email
        captured["otp"] = otp

    monkeypatch.setattr(
        "app.services.email_service.EmailService.send_email_verification",
        fake_send,
    )


def test_signup_sends_verification_otp(client, api_prefix, signup_payload, monkeypatch):
    captured: dict[str, str] = {}
    _capture_verification_email(monkeypatch, captured)

    response = client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    assert response.status_code == 201
    assert captured["to_email"] == signup_payload["email"].lower()
    assert len(captured["otp"]) == 6
    assert captured["otp"].isdigit()

    token_hash = hash_otp(captured["otp"])
    db = SessionLocal()
    try:
        row = EmailVerificationRepository(db).get_by_token_hash(token_hash)
        assert row is not None
        assert row.used_at is None
    finally:
        db.close()


def test_verify_otp_allows_login(client, api_prefix, signup_payload, monkeypatch):
    captured: dict[str, str] = {}
    _capture_verification_email(monkeypatch, captured)

    client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    verify = client.post(
        f"{api_prefix}/auth/verify-otp",
        json={"email": signup_payload["email"], "otp": captured["otp"]},
    )
    assert verify.status_code == 200
    assert "verified successfully" in verify.json()["message"].lower()

    login = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert login.status_code == 200
    assert login.json()["access_token"]
    assert login.json()["user"]["emailVerified"] is True

    reuse = client.post(
        f"{api_prefix}/auth/verify-otp",
        json={"email": signup_payload["email"], "otp": captured["otp"]},
    )
    assert reuse.status_code == 400
    assert reuse.json()["detail"] == "Invalid or expired OTP"


def test_verify_otp_rejects_invalid_code(client, api_prefix, signup_payload, monkeypatch):
    _capture_verification_email(monkeypatch, {})
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    response = client.post(
        f"{api_prefix}/auth/verify-otp",
        json={"email": signup_payload["email"], "otp": "000000"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OTP"


def test_verify_otp_rejects_expired_code(client, api_prefix, signup_payload, monkeypatch):
    captured: dict[str, str] = {}
    _capture_verification_email(monkeypatch, captured)

    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    token_hash = hash_otp(captured["otp"])

    db = SessionLocal()
    try:
        row = EmailVerificationRepository(db).get_by_token_hash(token_hash)
        assert row is not None
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"{api_prefix}/auth/verify-otp",
        json={"email": signup_payload["email"], "otp": captured["otp"]},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OTP"


def test_resend_verification_sends_new_otp(client, api_prefix, signup_payload, monkeypatch):
    captured: dict[str, str] = {}
    _capture_verification_email(monkeypatch, captured)

    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    first_otp = captured["otp"]

    response = client.post(
        f"{api_prefix}/auth/resend-verification",
        json={"email": signup_payload["email"]},
    )
    assert response.status_code == 200
    assert "verification code" in response.json()["message"].lower()

    second_otp = captured["otp"]
    assert second_otp != first_otp

    old = client.post(
        f"{api_prefix}/auth/verify-otp",
        json={"email": signup_payload["email"], "otp": first_otp},
    )
    assert old.status_code == 400

    ok = client.post(
        f"{api_prefix}/auth/verify-otp",
        json={"email": signup_payload["email"], "otp": second_otp},
    )
    assert ok.status_code == 200


def test_resend_verification_generic_for_unknown_email(client, api_prefix):
    response = client.post(
        f"{api_prefix}/auth/resend-verification",
        json={"email": f"missing-{uuid4().hex}@gmail.com"},
    )

    assert response.status_code == 200
    assert "verification code" in response.json()["message"].lower()
