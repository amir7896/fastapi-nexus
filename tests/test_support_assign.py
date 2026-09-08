from tests.conftest import login_headers
from tests.test_staff_roles import staff_headers
from app.models.user import UserRole


def test_support_staff_can_claim_and_release_a_ticket(client, api_prefix, signup_payload):
    customer = login_headers(client, api_prefix, signup_payload)
    created = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "GENERAL", "subject": "Need help", "message": "Hi"},
        headers=customer,
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation"]["id"]

    first = staff_headers(client, api_prefix, UserRole.SUPPORT)
    claimed = client.post(
        f"{api_prefix}/support/conversations/{conversation_id}/assign-me",
        headers=first,
    )
    assert claimed.status_code == 200, claimed.text
    body = claimed.json()["conversation"]
    assert body["assignedToName"]
    assert body["assignedToId"]

    mine = client.get(f"{api_prefix}/support/conversations?assignedToMe=true", headers=first)
    assert mine.status_code == 200, mine.text
    assert any(item["id"] == conversation_id for item in mine.json()["data"])

    second = staff_headers(client, api_prefix, UserRole.SUPPORT)
    inbox = client.get(f"{api_prefix}/support/conversations?unassigned=true", headers=second)
    assert inbox.status_code == 200, inbox.text
    assert all(item["id"] != conversation_id for item in inbox.json()["data"])

    released = client.post(
        f"{api_prefix}/support/conversations/{conversation_id}/unassign",
        headers=first,
    )
    assert released.status_code == 200, released.text
    assert released.json()["conversation"]["assignedToId"] is None

    open_inbox = client.get(f"{api_prefix}/support/conversations?unassigned=true", headers=second)
    assert any(item["id"] == conversation_id for item in open_inbox.json()["data"])


def test_customers_cannot_claim_tickets(client, api_prefix, signup_payload):
    customer = login_headers(client, api_prefix, signup_payload)
    created = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "GENERAL", "subject": "Need help", "message": "Hi"},
        headers=customer,
    )
    conversation_id = created.json()["conversation"]["id"]
    response = client.post(
        f"{api_prefix}/support/conversations/{conversation_id}/assign-me",
        headers=customer,
    )
    assert response.status_code == 403
