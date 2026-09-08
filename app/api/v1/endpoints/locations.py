from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, LocationServiceDep
from app.schemas.location import LocationListResponse, PhoneCodeListResponse, PhoneCodeRead

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get(
    "/countries",
    response_model=LocationListResponse,
    summary="List countries for address dropdowns",
)
def list_countries(
    current_user: CurrentUserDep,
    location_service: LocationServiceDep,
) -> LocationListResponse:
    return LocationListResponse(
        message="Countries fetched successfully",
        data=location_service.list_countries(),
    )


@router.get(
    "/states",
    response_model=LocationListResponse,
    summary="List states for a country",
)
def list_states(
    current_user: CurrentUserDep,
    location_service: LocationServiceDep,
    country: str = Query(..., min_length=2, max_length=80),
) -> LocationListResponse:
    return LocationListResponse(
        message="States fetched successfully",
        data=location_service.list_states(country),
    )


@router.get(
    "/cities",
    response_model=LocationListResponse,
    summary="List cities for a country and state",
)
def list_cities(
    current_user: CurrentUserDep,
    location_service: LocationServiceDep,
    country: str = Query(..., min_length=2, max_length=80),
    state: str = Query(..., min_length=1, max_length=80),
) -> LocationListResponse:
    return LocationListResponse(
        message="Cities fetched successfully",
        data=location_service.list_cities(country, state),
    )


@router.get(
    "/phone-codes",
    response_model=PhoneCodeListResponse,
    summary="List phone country codes",
)
def list_phone_codes(
    current_user: CurrentUserDep,
    location_service: LocationServiceDep,
) -> PhoneCodeListResponse:
    return PhoneCodeListResponse(
        message="Phone country codes fetched successfully",
        data=[
            PhoneCodeRead(
                country=item.country,
                iso2=item.iso2,
                dial_code=item.dial_code,
                flag=item.flag,
                example=item.example,
                national_length=item.national_length,
                max_national_length=item.max_national_length,
            )
            for item in location_service.list_phone_codes()
        ],
    )
