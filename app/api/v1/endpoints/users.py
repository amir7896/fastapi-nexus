from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, UserServiceDep
from app.api.pagination import PaginationDep
from app.schemas.user import UserListResponse, UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users with search and pagination",
)
def list_users(
    _: CurrentUserDep,
    pagination: PaginationDep,
    user_service: UserServiceDep,
) -> UserListResponse:
    return user_service.list_users(pagination)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user by id",
)
def get_user(
    user_id: UUID,
    _: CurrentUserDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return user_service.get_user(user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user (own profile, or any user if admin)",
)
def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return user_service.update_user(user_id, payload, current_user=current_user)


@router.delete(
    "/{user_id}",
    response_model=UserResponse,
    summary="Delete a user (admin only)",
)
def delete_user(
    user_id: UUID,
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return user_service.delete_user(user_id, current_user=current_user)
