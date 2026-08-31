from tests.conftest import login_headers


def test_change_password_requires_authentication(client, api_prefix):
    response = client.post(
        f"{api_prefix}/auth/change-password",
        json={
            "currentPassword": "Secret123",
            "newPassword": "NewSecret123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_change_password_rejects_wrong_current_password(
    client,
    api_prefix,
    signup_payload,
):
    headers = login_headers(client, api_prefix, signup_payload)

    response = client.post(
        f"{api_prefix}/auth/change-password",
        headers=headers,
        json={
            "currentPassword": "WrongPass123",
            "newPassword": "NewSecret123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Current password is incorrect"


def test_change_password_rejects_same_password(client, api_prefix, signup_payload):
    headers = login_headers(client, api_prefix, signup_payload)

    response = client.post(
        f"{api_prefix}/auth/change-password",
        headers=headers,
        json={
            "currentPassword": signup_payload["password"],
            "newPassword": signup_payload["password"],
        },
    )

    assert response.status_code == 400
    assert "different" in response.json()["detail"].lower()


def test_change_password_updates_password(client, api_prefix, signup_payload):
    headers = login_headers(client, api_prefix, signup_payload)
    new_password = "NewSecret123"

    response = client.post(
        f"{api_prefix}/auth/change-password",
        headers=headers,
        json={
            "currentPassword": signup_payload["password"],
            "newPassword": new_password,
        },
    )

    assert response.status_code == 200
    assert "changed successfully" in response.json()["message"].lower()

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
        json={
            "email": signup_payload["email"],
            "password": new_password,
        },
    )
    assert new_login.status_code == 200
    assert new_login.json()["access_token"]
