from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentAdminDep, UserServiceDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.user import UserListResponse, UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Admin — Users"])


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
)
def list_users(
    page: PageQuery = 1,
    limit: LimitQuery = 10,
    search: SearchQuery = None,
    _: CurrentAdminDep = None,
    user_service: UserServiceDep = None,
) -> UserListResponse:
    return user_service.list_users(build_pagination(page, limit, search))


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user by id",
)
def get_user(
    user_id: UUID,
    _: CurrentAdminDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return user_service.get_user(user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update any user",
)
def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    current_admin: CurrentAdminDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return user_service.update_user(user_id, payload, current_user=current_admin)


@router.delete(
    "/{user_id}",
    response_model=UserResponse,
    summary="Delete a user",
)
def delete_user(
    user_id: UUID,
    current_admin: CurrentAdminDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return user_service.delete_user(user_id, current_user=current_admin)
