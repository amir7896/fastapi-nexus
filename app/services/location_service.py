from dataclasses import dataclass
from functools import lru_cache
import re

import httpx
import phonenumbers
from phonenumbers import NumberParseException

from app.core.exceptions import BadRequestError

COUNTRIESNOW_BASE = "https://countriesnow.space/api/v0.1"
TIMEOUT = 20.0


@dataclass(frozen=True)
class PhoneCode:
    country: str
    iso2: str
    dial_code: str
    flag: str
    example: str = ""
    national_length: int = 0
    max_national_length: int = 0


class LocationService:
    def list_countries(self) -> list[str]:
        return self._countries()

    def list_states(self, country: str) -> list[str]:
        canonical = self._require_country(country)
        states = self._states(canonical)
        return states or [canonical]

    def list_cities(self, country: str, state: str) -> list[str]:
        canonical_country = self._require_country(country)
        canonical_state = self._require_state(canonical_country, state)
        cities = self._cities(canonical_country, canonical_state)
        if cities:
            return cities
        return self._country_cities(canonical_country)

    def list_phone_codes(self) -> list[PhoneCode]:
        return [self._with_phone_guide(item) for item in self._phone_codes()]

    def canonicalize(self, *, country: str, state: str, city: str) -> tuple[str, str, str]:
        canonical_country = self._require_country(country)
        canonical_state = self._require_state(canonical_country, state)
        canonical_city = self._match(city, self.list_cities(canonical_country, canonical_state))
        if canonical_city is None:
            raise BadRequestError("Select a valid city")
        return canonical_country, canonical_state, canonical_city

    def canonicalize_phone(
        self,
        *,
        dial_code: str,
        number: str,
        country: str | None = None,
    ) -> tuple[str, str]:
        matched = self._require_phone_code(dial_code, country=country)
        digits = re.sub(r"\D", "", number)
        if not digits:
            raise BadRequestError("Enter a valid phone")
        parsed = self._parse_phone(digits, matched)
        if parsed is None or not phonenumbers.is_valid_number(parsed):
            raise BadRequestError(self._invalid_phone_message(matched))
        return matched.dial_code, str(parsed.national_number)

    def _require_country(self, country: str) -> str:
        matched = self._match(country, self.list_countries())
        if matched is None:
            raise BadRequestError("Select a valid country")
        return matched

    def _require_state(self, country: str, state: str) -> str:
        matched = self._match(state, self.list_states(country))
        if matched is None:
            raise BadRequestError("Select a valid state")
        return matched

    def _require_phone_code(self, dial_code: str, country: str | None = None) -> PhoneCode:
        needle = self._normalize_dial(dial_code)
        codes = [item for item in self.list_phone_codes() if item.dial_code == needle]
        if not codes:
            raise BadRequestError("Select a valid phone country code")
        if country:
            named = self._match_phone_country(country, codes)
            if named is not None:
                return named
        return codes[0]

    @staticmethod
    def _parse_phone(digits: str, matched: PhoneCode):
        try:
            parsed = phonenumbers.parse(f"{matched.dial_code}{digits}", None)
        except NumberParseException:
            parsed = None
        if parsed is not None:
            return parsed
        try:
            return phonenumbers.parse(digits, matched.iso2)
        except NumberParseException:
            return None

    @staticmethod
    def _match(value: str, options: list[str]) -> str | None:
        needle = value.strip().casefold()
        if not needle:
            return None
        for option in options:
            if option.casefold() == needle:
                return option
        return None

    @staticmethod
    def _match_phone_country(country: str, codes: list[PhoneCode]) -> PhoneCode | None:
        needle = country.strip().casefold()
        if not needle:
            return None
        for item in codes:
            if item.country.casefold() == needle:
                return item
        for item in codes:
            name = item.country.casefold()
            if needle in name or name in needle:
                return item
        return None

    @staticmethod
    def _invalid_phone_message(matched: PhoneCode) -> str:
        example = matched.example or LocationService._phone_guide(matched.iso2)[0]
        if example:
            return f"That doesn't look like a {matched.country} number. Try {example}."
        return f"Enter a valid {matched.country} phone number"

    @staticmethod
    def _with_phone_guide(item: PhoneCode) -> PhoneCode:
        example, length, maximum = LocationService._phone_guide(item.iso2)
        return PhoneCode(
            country=item.country,
            iso2=item.iso2,
            dial_code=item.dial_code,
            flag=item.flag,
            example=example,
            national_length=length,
            max_national_length=maximum,
        )

    @staticmethod
    @lru_cache(maxsize=512)
    def _phone_guide(iso2: str) -> tuple[str, int, int]:
        region = iso2.strip().upper()
        example_number = (
            phonenumbers.example_number_for_type(region, phonenumbers.PhoneNumberType.MOBILE)
            or phonenumbers.example_number_for_type(
                region, phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE
            )
            or phonenumbers.example_number(region)
        )
        example = ""
        length = 0
        if example_number is not None:
            example = phonenumbers.format_number(
                example_number, phonenumbers.PhoneNumberFormat.NATIONAL
            )
            length = len(str(example_number.national_number))
        maximum = length
        metadata = phonenumbers.PhoneMetadata.metadata_for_region(region)
        possible = getattr(getattr(metadata, "general_desc", None), "possible_length", None)
        if possible:
            maximum = max(int(item) for item in possible)
        return example, length, maximum or 15

    @staticmethod
    def _normalize_dial(value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if not digits:
            return ""
        return f"+{digits}"

    @staticmethod
    @lru_cache(maxsize=1)
    def _countries() -> list[str]:
        payload = LocationService._get("/countries/positions")
        names = [str(item.get("name", "")).strip() for item in payload if isinstance(item, dict)]
        return sorted({name for name in names if name})

    @staticmethod
    @lru_cache(maxsize=512)
    def _states(country: str) -> list[str]:
        payload = LocationService._get("/countries/states/q", {"country": country})
        raw = payload.get("states") if isinstance(payload, dict) else payload
        if not isinstance(raw, list):
            return []
        names = []
        for item in raw:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
            else:
                name = str(item).strip()
            if name:
                names.append(name)
        return names

    @staticmethod
    @lru_cache(maxsize=2048)
    def _cities(country: str, state: str) -> list[str]:
        payload = LocationService._get(
            "/countries/state/cities/q",
            {"country": country, "state": state},
        )
        if not isinstance(payload, list):
            return []
        return [str(name).strip() for name in payload if str(name).strip()]

    @staticmethod
    @lru_cache(maxsize=256)
    def _country_cities(country: str) -> list[str]:
        payload = LocationService._get("/countries/cities/q", {"country": country})
        if not isinstance(payload, list):
            return []
        return [str(name).strip() for name in payload if str(name).strip()]

    @staticmethod
    @lru_cache(maxsize=1)
    def _phone_codes() -> tuple[PhoneCode, ...]:
        payload = LocationService._get("/countries/codes")
        if not isinstance(payload, list):
            raise BadRequestError("Phone country codes are unavailable")
        by_iso: dict[str, PhoneCode] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            country = str(item.get("name") or "").strip()
            iso2 = str(item.get("code") or "").strip().upper()
            dial = LocationService._normalize_dial(str(item.get("dial_code") or ""))
            if not country or not iso2 or not dial:
                continue
            by_iso[iso2] = PhoneCode(country=country, iso2=iso2, dial_code=dial, flag="")
        return tuple(sorted(by_iso.values(), key=lambda item: item.country.casefold()))

    @staticmethod
    def _get(path: str, params: dict | None = None):
        return LocationService._request("GET", path, params=params)

    @staticmethod
    def _request(method: str, path: str, *, body: dict | None = None, params: dict | None = None):
        try:
            response = httpx.request(
                method,
                f"{COUNTRIESNOW_BASE}{path}",
                json=body,
                params=params,
                timeout=TIMEOUT,
                follow_redirects=True,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise BadRequestError("Location data is unavailable") from exc
        if not isinstance(payload, dict):
            raise BadRequestError("Location data is unavailable")
        if payload.get("error"):
            raise BadRequestError(str(payload.get("msg") or "Location data is unavailable"))
        return payload.get("data")
