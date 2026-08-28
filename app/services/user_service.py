from uuid import UUID

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.pagination import PaginationQuery, build_pagination_meta
from app.schemas.user import (
    UserListResponse,
    UserRead,
    UserResponse,
    UserUpdateRequest,
)

logger = get_logger(__name__)


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def list_users(self, pagination: PaginationQuery) -> UserListResponse:
        items, total = self._users.list_paginated(
            page=pagination.page,
            limit=pagination.limit,
            search=pagination.search,
        )
        return UserListResponse(
            message="Users fetched successfully",
            data=[UserRead.model_validate(item) for item in items],
            meta=build_pagination_meta(
                total=total,
                page=pagination.page,
                limit=pagination.limit,
            ),
        )

    def get_user(self, user_id: UUID) -> UserResponse:
        user = self._get_user(user_id)
        return UserResponse(
            message="User fetched successfully",
            user=UserRead.model_validate(user),
        )

    def update_user(
        self,
        user_id: UUID,
        payload: UserUpdateRequest,
        *,
        current_user: User,
    ) -> UserResponse:
        if current_user.id != user_id and current_user.role is not UserRole.ADMIN:
            raise ForbiddenError("You can only update your own profile")

        user = self._get_user(user_id)
        updated = self._users.update(user, name=payload.name, age=payload.age)
        logger.info("Updated user %s", updated.id)

        return UserResponse(
            message="User updated successfully",
            user=UserRead.model_validate(updated),
        )

    def delete_user(self, user_id: UUID, *, current_user: User) -> UserResponse:
        if current_user.role is not UserRole.ADMIN:
            raise ForbiddenError("Admin access required")

        if current_user.id == user_id:
            raise ForbiddenError("Admins cannot delete their own account")

        user = self._get_user(user_id)
        snapshot = UserRead.model_validate(user)
        self._users.delete(user)
        logger.info("Deleted user %s", user_id)

        return UserResponse(
            message="User deleted successfully",
            user=snapshot,
        )

    def _get_user(self, user_id: UUID) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user
