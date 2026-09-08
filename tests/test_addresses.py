from uuid import uuid4

from tests.conftest import login_headers
from tests.test_locations import install_location_catalog


def _address_payload(**overrides):
    data = {
        "name": "Amir Shahzad",
        "phoneCountryCode": "+92",
        "phone": "3001234567",
        "address": "12 Market Street",
        "city": "Lahore",
        "state": "Punjab",
        "country": "Pakistan",
        "label": "Home",
    }
    data.update(overrides)
    return data


def test_address_book_crud_and_default(client, api_prefix, signup_payload, monkeypatch):
    install_location_catalog(monkeypatch)
    headers = login_headers(client, api_prefix, signup_payload)

    empty = client.get(f"{api_prefix}/addresses", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["data"] == []

    created = client.post(f"{api_prefix}/addresses", json=_address_payload(), headers=headers)
    assert created.status_code == 201, created.text
    home = created.json()["address"]
    assert home["isDefault"] is True
    assert home["label"] == "Home"
    assert home["phoneCountryCode"] == "+92"
    assert home["phone"] == "3001234567"
    home_id = home["id"]

    work = client.post(
        f"{api_prefix}/addresses",
        json=_address_payload(label="Work", city="Karachi", state="Sindh", isDefault=True),
        headers=headers,
    )
    assert work.status_code == 201, work.text
    work_id = work.json()["address"]["id"]
    assert work.json()["address"]["isDefault"] is True

    listing = client.get(f"{api_prefix}/addresses", headers=headers)
    assert listing.status_code == 200
    rows = listing.json()["data"]
    assert len(rows) == 2
    by_id = {row["id"]: row for row in rows}
    assert by_id[work_id]["isDefault"] is True
    assert by_id[home_id]["isDefault"] is False

    updated = client.put(
        f"{api_prefix}/addresses/{home_id}",
        json=_address_payload(label="Parents", city="Islamabad", state="Islamabad Capital Territory"),
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["address"]["city"] == "Islamabad"
    assert updated.json()["address"]["state"] == "Islamabad Capital Territory"
    assert updated.json()["address"]["isDefault"] is False

    defaulted = client.post(f"{api_prefix}/addresses/{home_id}/default", headers=headers)
    assert defaulted.status_code == 200
    assert defaulted.json()["address"]["isDefault"] is True

    deleted = client.delete(f"{api_prefix}/addresses/{home_id}", headers=headers)
    assert deleted.status_code == 200
    remaining = deleted.json()["data"]
    assert len(remaining) == 1
    assert remaining[0]["id"] == work_id
    assert remaining[0]["isDefault"] is True


def test_address_book_is_private_and_capped(client, api_prefix, signup_payload, monkeypatch):
    install_location_catalog(monkeypatch)
    owner = login_headers(client, api_prefix, signup_payload)
    other = login_headers(
        client,
        api_prefix,
        {
            "name": "Other",
            "email": f"other-{uuid4().hex}@gmail.com",
            "password": "Secret123",
            "age": 30,
        },
    )

    created = client.post(f"{api_prefix}/addresses", json=_address_payload(), headers=owner)
    address_id = created.json()["address"]["id"]

    other_list = client.get(f"{api_prefix}/addresses", headers=other)
    assert other_list.status_code == 200
    assert other_list.json()["data"] == []

    forbidden = client.put(
        f"{api_prefix}/addresses/{address_id}",
        json=_address_payload(label="Stolen"),
        headers=other,
    )
    assert forbidden.status_code == 404

    missing = client.delete(f"{api_prefix}/addresses/{address_id}", headers=other)
    assert missing.status_code == 404

    for index in range(9):
        extra = client.post(
            f"{api_prefix}/addresses",
            json=_address_payload(label=f"Spot {index}", address=f"{index + 2} Market Street"),
            headers=owner,
        )
        assert extra.status_code == 201, extra.text

    overflow = client.post(
        f"{api_prefix}/addresses",
        json=_address_payload(label="Overflow", address="99 Market Street"),
        headers=owner,
    )
    assert overflow.status_code == 400
    assert "10" in overflow.json()["detail"]


def test_address_rejects_unknown_city(client, api_prefix, signup_payload, monkeypatch):
    install_location_catalog(monkeypatch)
    headers = login_headers(client, api_prefix, signup_payload)
    invalid = client.post(
        f"{api_prefix}/addresses",
        json=_address_payload(city="Narnia", state="Punjab"),
        headers=headers,
    )
    assert invalid.status_code == 400


def test_address_rejects_invalid_phone(client, api_prefix, signup_payload, monkeypatch):
    install_location_catalog(monkeypatch)
    headers = login_headers(client, api_prefix, signup_payload)
    invalid = client.post(
        f"{api_prefix}/addresses",
        json=_address_payload(phone="300123"),
        headers=headers,
    )
    assert invalid.status_code == 400
    assert "Try" in invalid.json()["detail"]

    unknown_code = client.post(
        f"{api_prefix}/addresses",
        json=_address_payload(phoneCountryCode="+999"),
        headers=headers,
    )
    assert unknown_code.status_code == 400


def test_addresses_require_auth(client, api_prefix):
    response = client.get(f"{api_prefix}/addresses")
    assert response.status_code == 401
