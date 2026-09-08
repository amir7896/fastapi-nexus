from uuid import UUID

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.saved_address import SavedAddress
from app.models.user import User
from app.repositories.address_repository import AddressRepository
from app.schemas.address import (
    SavedAddressCreateRequest,
    SavedAddressListResponse,
    SavedAddressRead,
    SavedAddressResponse,
    SavedAddressUpdateRequest,
)
from app.services.location_service import LocationService

MAX_SAVED_ADDRESSES = 10


class AddressService:
    def __init__(self, addresses: AddressRepository, locations: LocationService) -> None:
        self._addresses = addresses
        self._locations = locations

    def list_addresses(self, current_user: User) -> SavedAddressListResponse:
        items = self._addresses.list_by_user(current_user.id)
        return SavedAddressListResponse(
            message="Addresses fetched successfully",
            data=[SavedAddressRead.model_validate(item) for item in items],
        )

    def create_address(
        self,
        payload: SavedAddressCreateRequest,
        *,
        current_user: User,
    ) -> SavedAddressResponse:
        existing = self._addresses.list_by_user(current_user.id)
        if len(existing) >= MAX_SAVED_ADDRESSES:
            raise BadRequestError(f"You can save up to {MAX_SAVED_ADDRESSES} addresses")

        is_default = payload.is_default or len(existing) == 0
        if is_default:
            self._addresses.clear_defaults(current_user.id)

        country, state, city = self._locations.canonicalize(
            country=payload.country,
            state=payload.state,
            city=payload.city,
        )
        phone_country_code, phone = self._locations.canonicalize_phone(
            dial_code=payload.phone_country_code,
            number=payload.phone,
            country=country,
        )
        item = self._addresses.create(
            user_id=current_user.id,
            label=self._normalize_label(payload.label),
            name=payload.name.strip(),
            phone_country_code=phone_country_code,
            phone=phone,
            address=payload.address.strip(),
            city=city,
            state=state,
            country=country,
            is_default=is_default,
        )
        return SavedAddressResponse(message="Address saved", address=SavedAddressRead.model_validate(item))

    def update_address(
        self,
        address_id: UUID,
        payload: SavedAddressUpdateRequest,
        *,
        current_user: User,
    ) -> SavedAddressResponse:
        item = self._require_owned(address_id, current_user.id)
        others = [row for row in self._addresses.list_by_user(current_user.id) if row.id != item.id]
        is_default = payload.is_default or not others
        if is_default:
            self._addresses.clear_defaults(current_user.id, except_id=item.id)

        country, state, city = self._locations.canonicalize(
            country=payload.country,
            state=payload.state,
            city=payload.city,
        )
        phone_country_code, phone = self._locations.canonicalize_phone(
            dial_code=payload.phone_country_code,
            number=payload.phone,
            country=country,
        )
        item.label = self._normalize_label(payload.label)
        item.name = payload.name.strip()
        item.phone_country_code = phone_country_code
        item.phone = phone
        item.address = payload.address.strip()
        item.city = city
        item.state = state
        item.country = country
        item.is_default = is_default
        saved = self._addresses.save(item)
        return SavedAddressResponse(message="Address updated", address=SavedAddressRead.model_validate(saved))

    def delete_address(self, address_id: UUID, *, current_user: User) -> SavedAddressListResponse:
        item = self._require_owned(address_id, current_user.id)
        was_default = item.is_default
        self._addresses.delete(item)
        remaining = self._addresses.list_by_user(current_user.id)
        if was_default and remaining:
            remaining[0].is_default = True
            self._addresses.save(remaining[0])
            remaining = self._addresses.list_by_user(current_user.id)
        return SavedAddressListResponse(
            message="Address deleted",
            data=[SavedAddressRead.model_validate(row) for row in remaining],
        )

    def set_default(self, address_id: UUID, *, current_user: User) -> SavedAddressResponse:
        item = self._require_owned(address_id, current_user.id)
        self._addresses.clear_defaults(current_user.id, except_id=item.id)
        item.is_default = True
        saved = self._addresses.save(item)
        return SavedAddressResponse(
            message="Default address updated",
            address=SavedAddressRead.model_validate(saved),
        )

    def _require_owned(self, address_id: UUID, user_id: UUID) -> SavedAddress:
        item = self._addresses.get_for_user(address_id, user_id)
        if item is None:
            raise NotFoundError("Address not found")
        return item

    @staticmethod
    def _normalize_label(label: str | None) -> str | None:
        if label is None:
            return None
        stripped = label.strip()
        return stripped or None
