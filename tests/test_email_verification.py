from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.security import hash_password_reset_token
from app.db.session import SessionLocal
from app.repositories.email_verification_repository import EmailVerificationRepository


def _capture_verification_email(monkeypatch, captured: dict[str, str]) -> None:
    def fake_send(self, *, to_email: str, verify_url: str) -> None:
        captured["to_email"] = to_email
        captured["verify_url"] = verify_url

    monkeypatch.setattr(
        "app.services.email_service.EmailService.send_email_verification",
        fake_send,
    )


def test_signup_sends_verification_email(client, api_prefix, signup_payload, monkeypatch):
    captured: dict[str, str] = {}
    _capture_verification_email(monkeypatch, captured)

    response = client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    assert response.status_code == 201
    assert captured["to_email"] == signup_payload["email"].lower()
    assert "token=" in captured["verify_url"]

    raw_token = captured["verify_url"].split("token=", 1)[1]
    token_hash = hash_password_reset_token(raw_token)

    db = SessionLocal()
    try:
        row = EmailVerificationRepository(db).get_by_token_hash(token_hash)
        assert row is not None
        assert row.used_at is None
    finally:
        db.close()


def test_verify_email_allows_login(client, api_prefix, signup_payload, monkeypatch):
    captured: dict[str, str] = {}
    _capture_verification_email(monkeypatch, captured)

    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    raw_token = captured["verify_url"].split("token=", 1)[1]

    verify = client.post(
        f"{api_prefix}/auth/verify-email",
        json={"token": raw_token},
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
        f"{api_prefix}/auth/verify-email",
        json={"token": raw_token},
    )
    assert reuse.status_code == 400
    assert reuse.json()["detail"] == "Invalid or expired verification token"


def test_verify_email_rejects_invalid_token(client, api_prefix):
    response = client.post(
        f"{api_prefix}/auth/verify-email",
        json={"token": "this-is-not-a-valid-verify-token-value"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification token"


def test_verify_email_rejects_expired_token(client, api_prefix, signup_payload, monkeypatch):
    captured: dict[str, str] = {}
    _capture_verification_email(monkeypatch, captured)

    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    raw_token = captured["verify_url"].split("token=", 1)[1]
    token_hash = hash_password_reset_token(raw_token)

    db = SessionLocal()
    try:
        row = EmailVerificationRepository(db).get_by_token_hash(token_hash)
        assert row is not None
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"{api_prefix}/auth/verify-email",
        json={"token": raw_token},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification token"


def test_resend_verification_sends_new_token(client, api_prefix, signup_payload, monkeypatch):
    captured: dict[str, str] = {}
    _capture_verification_email(monkeypatch, captured)

    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    first_token = captured["verify_url"].split("token=", 1)[1]

    response = client.post(
        f"{api_prefix}/auth/resend-verification",
        json={"email": signup_payload["email"]},
    )
    assert response.status_code == 200
    assert "verification link" in response.json()["message"].lower()

    second_token = captured["verify_url"].split("token=", 1)[1]
    assert second_token != first_token

    old = client.post(f"{api_prefix}/auth/verify-email", json={"token": first_token})
    assert old.status_code == 400

    ok = client.post(f"{api_prefix}/auth/verify-email", json={"token": second_token})
    assert ok.status_code == 200


def test_resend_verification_generic_for_unknown_email(client, api_prefix):
    response = client.post(
        f"{api_prefix}/auth/resend-verification",
        json={"email": f"missing-{uuid4().hex}@gmail.com"},
    )

    assert response.status_code == 200
    assert "verification link" in response.json()["message"].lower()
