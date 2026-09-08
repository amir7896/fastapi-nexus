from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import AddressServiceDep, CurrentUserDep
from app.schemas.address import (
    SavedAddressCreateRequest,
    SavedAddressListResponse,
    SavedAddressResponse,
    SavedAddressUpdateRequest,
)

router = APIRouter(prefix="/addresses", tags=["Addresses"])


@router.get(
    "",
    response_model=SavedAddressListResponse,
    response_model_by_alias=True,
    summary="List saved shipping addresses",
)
def list_addresses(
    current_user: CurrentUserDep,
    address_service: AddressServiceDep,
) -> SavedAddressListResponse:
    return address_service.list_addresses(current_user)


@router.post(
    "",
    response_model=SavedAddressResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Save a shipping address",
)
def create_address(
    payload: SavedAddressCreateRequest,
    current_user: CurrentUserDep,
    address_service: AddressServiceDep,
) -> SavedAddressResponse:
    return address_service.create_address(payload, current_user=current_user)


@router.put(
    "/{address_id}",
    response_model=SavedAddressResponse,
    response_model_by_alias=True,
    summary="Update a saved shipping address",
)
def update_address(
    address_id: UUID,
    payload: SavedAddressUpdateRequest,
    current_user: CurrentUserDep,
    address_service: AddressServiceDep,
) -> SavedAddressResponse:
    return address_service.update_address(address_id, payload, current_user=current_user)


@router.post(
    "/{address_id}/default",
    response_model=SavedAddressResponse,
    response_model_by_alias=True,
    summary="Mark a saved address as the default",
)
def set_default_address(
    address_id: UUID,
    current_user: CurrentUserDep,
    address_service: AddressServiceDep,
) -> SavedAddressResponse:
    return address_service.set_default(address_id, current_user=current_user)


@router.delete(
    "/{address_id}",
    response_model=SavedAddressListResponse,
    response_model_by_alias=True,
    summary="Delete a saved shipping address",
)
def delete_address(
    address_id: UUID,
    current_user: CurrentUserDep,
    address_service: AddressServiceDep,
) -> SavedAddressListResponse:
    return address_service.delete_address(address_id, current_user=current_user)
