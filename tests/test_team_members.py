from uuid import uuid4

from app.models.user import UserRole
from tests.test_organizations import _merchant_headers


def test_admin_can_deactivate_and_remove_staff(client, api_prefix, monkeypatch):
    captured: dict = {}

    def capture_invite(self, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        "app.services.email_service.EmailService.send_staff_invite",
        capture_invite,
    )

    admin = _merchant_headers(client, api_prefix, "Team Shop")
    invite_email = f"mgr-{uuid4().hex}@gmail.com"
    created = client.post(
        f"{api_prefix}/organizations/invites",
        json={"email": invite_email, "role": UserRole.MANAGER.value},
        headers=admin,
    )
    assert created.status_code == 201, created.text
    token = captured["accept_url"].rstrip("/").rsplit("/", 1)[-1]
    accepted = client.post(
        f"{api_prefix}/organizations/invites/accept",
        json={"token": token, "name": "Pat Manager", "password": "Secret123"},
    )
    assert accepted.status_code == 200, accepted.text
    manager_id = accepted.json()["user"]["id"]
    manager_token = accepted.json()["access_token"]

    team = client.get(f"{api_prefix}/organizations/team", headers=admin)
    assert team.status_code == 200, team.text
    member = next(item for item in team.json()["members"] if item["userId"] == manager_id)
    assert member["isActive"] is True

    deactivated = client.patch(
        f"{api_prefix}/organizations/team/{manager_id}",
        json={"isActive": False},
        headers=admin,
    )
    assert deactivated.status_code == 200, deactivated.text
    updated = next(item for item in deactivated.json()["members"] if item["userId"] == manager_id)
    assert updated["isActive"] is False

    blocked = client.get(
        f"{api_prefix}/organizations/current",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert blocked.status_code == 403

    removed = client.delete(f"{api_prefix}/organizations/team/{manager_id}", headers=admin)
    assert removed.status_code == 200, removed.text
    leftover = client.get(f"{api_prefix}/organizations/team", headers=admin).json()["members"]
    assert all(item["userId"] != manager_id for item in leftover)
