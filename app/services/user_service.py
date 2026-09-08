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
from app.services.audit_service import AuditService

logger = get_logger(__name__)


class UserService:
    def __init__(self, users: UserRepository, audit: AuditService | None = None) -> None:
        self._users = users
        self._audit = audit

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
        next_role = payload.role
        if next_role is not None:
            if current_user.role is not UserRole.ADMIN:
                raise ForbiddenError("Only admins can change a user role")
            if current_user.id == user_id and next_role is not UserRole.ADMIN:
                raise ForbiddenError("Admins cannot change their own role")
        if payload.email_verified is not None:
            if current_user.role is not UserRole.ADMIN:
                raise ForbiddenError("Only admins can change verification")
            if current_user.id == user_id:
                raise ForbiddenError("Admins cannot change their own verification")
        previous_role = user.role
        previous_verified = user.email_verified
        updated = self._users.update(
            user,
            name=payload.name,
            age=payload.age,
            role=next_role,
            email_verified=payload.email_verified,
            notify_order_email=payload.notify_order_email,
            notify_support_email=payload.notify_support_email,
            notify_marketing_email=payload.notify_marketing_email,
        )
        logger.info("Updated user %s", updated.id)
        if self._audit is not None:
            if next_role is not None and next_role is not previous_role:
                self._audit.record(
                    actor=current_user,
                    action="user.role_changed",
                    target_type="user",
                    target_id=updated.id,
                    summary=f"Changed {updated.name}'s role from {previous_role.value} to {updated.role.value}",
                    extra={"from": previous_role.value, "to": updated.role.value},
                )
            if payload.email_verified is not None and payload.email_verified != previous_verified:
                self._audit.record(
                    actor=current_user,
                    action="user.verified" if updated.email_verified else "user.unverified",
                    target_type="user",
                    target_id=updated.id,
                    summary=(
                        f"Marked {updated.name} as verified"
                        if updated.email_verified
                        else f"Removed verification from {updated.name}"
                    ),
                    extra={"emailVerified": updated.email_verified},
                )

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
        if self._audit is not None:
            self._audit.record(
                actor=current_user,
                action="user.deleted",
                target_type="user",
                target_id=user_id,
                summary=f"Deleted user {snapshot.name} ({snapshot.email})",
                extra={"role": snapshot.role.value},
            )

        return UserResponse(
            message="User deleted successfully",
            user=snapshot,
        )

    def _get_user(self, user_id: UUID) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user
