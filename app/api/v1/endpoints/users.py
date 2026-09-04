from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, UserServiceDep
from app.schemas.user import UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update own profile",
)
def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
) -> UserResponse:
    return user_service.update_user(user_id, payload, current_user=current_user)
