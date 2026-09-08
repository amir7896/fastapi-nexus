from uuid import uuid4

from app.core.config import get_settings
from app.db.bootstrap import bootstrap_admin
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository


def test_bootstrap_creates_admin_once(client, api_prefix, monkeypatch):
    email = f"owner-{uuid4().hex}@gmail.com"
    password = "Hello@1234"
    settings = get_settings()
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_EMAIL", email)
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", password)
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_NAME", "Store Owner")

    bootstrap_admin()
    bootstrap_admin()

    db = SessionLocal()
    try:
        users = UserRepository(db)
        organizations = OrganizationRepository(db)
        user = users.get_by_email(email)
        assert user is not None
        assert user.role is UserRole.ADMIN
        assert user.email_verified is True
        org = organizations.get_by_slug(settings.DEFAULT_ORGANIZATION_SLUG)
        assert org is not None
        membership = organizations.get_membership(user.id, org.id)
        assert membership is not None
        assert membership.role is UserRole.ADMIN
        assert users.get_by_email(email).id == user.id
    finally:
        db.close()

    login = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["role"] == "ADMIN"


def test_bootstrap_skips_when_env_empty(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_EMAIL", "")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "")
    bootstrap_admin()
