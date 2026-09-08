from uuid import uuid4

from app.services.location_service import LocationService, PhoneCode
from tests.conftest import login_headers

LOCATION_CATALOG = {
    "Pakistan": {
        "Punjab": ["Lahore", "Faisalabad", "Rawalpindi"],
        "Sindh": ["Karachi", "Hyderabad"],
        "Islamabad Capital Territory": ["Islamabad"],
    }
}

PHONE_CODES = (
    PhoneCode(country="Pakistan", iso2="PK", dial_code="+92", flag="🇵🇰"),
    PhoneCode(country="United States", iso2="US", dial_code="+1", flag="🇺🇸"),
)


def install_location_catalog(monkeypatch) -> None:
    monkeypatch.setattr(
        LocationService,
        "_countries",
        staticmethod(lambda: list(LOCATION_CATALOG)),
    )
    monkeypatch.setattr(
        LocationService,
        "_states",
        staticmethod(lambda country: list(LOCATION_CATALOG.get(country, {}))),
    )
    monkeypatch.setattr(
        LocationService,
        "_cities",
        staticmethod(lambda country, state: list(LOCATION_CATALOG.get(country, {}).get(state, []))),
    )
    monkeypatch.setattr(LocationService, "_country_cities", staticmethod(lambda country: []))
    monkeypatch.setattr(LocationService, "_phone_codes", staticmethod(lambda: PHONE_CODES))


def test_location_dropdowns_cascade(client, api_prefix, signup_payload, monkeypatch):
    install_location_catalog(monkeypatch)
    headers = login_headers(client, api_prefix, signup_payload)

    countries = client.get(f"{api_prefix}/locations/countries", headers=headers)
    assert countries.status_code == 200
    assert "Pakistan" in countries.json()["data"]

    states = client.get(
        f"{api_prefix}/locations/states",
        params={"country": "Pakistan"},
        headers=headers,
    )
    assert states.status_code == 200
    assert "Punjab" in states.json()["data"]

    cities = client.get(
        f"{api_prefix}/locations/cities",
        params={"country": "Pakistan", "state": "Punjab"},
        headers=headers,
    )
    assert cities.status_code == 200
    assert "Lahore" in cities.json()["data"]

    unknown = client.get(
        f"{api_prefix}/locations/states",
        params={"country": "Narnia"},
        headers=headers,
    )
    assert unknown.status_code == 400


def test_phone_codes_list(client, api_prefix, signup_payload, monkeypatch):
    install_location_catalog(monkeypatch)
    headers = login_headers(client, api_prefix, signup_payload)

    response = client.get(f"{api_prefix}/locations/phone-codes", headers=headers)
    assert response.status_code == 200
    codes = response.json()["data"]
    pakistan = next(item for item in codes if item["iso2"] == "PK")
    assert pakistan["dialCode"] == "+92"
    assert pakistan["country"] == "Pakistan"
    assert pakistan["example"]
    assert pakistan["nationalLength"] >= 10
    united_states = next(item for item in codes if item["iso2"] == "US")
    assert united_states["example"]
    assert united_states["maxNationalLength"] == 10


def test_locations_require_auth(client, api_prefix):
    response = client.get(f"{api_prefix}/locations/countries")
    assert response.status_code == 401
    codes = client.get(f"{api_prefix}/locations/phone-codes")
    assert codes.status_code == 401
