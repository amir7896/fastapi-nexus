from uuid import UUID

from app.core.logging import get_logger
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import StaffAuditLogListResponse, StaffAuditLogRead
from app.schemas.pagination import PaginationQuery, build_pagination_meta

logger = get_logger(__name__)


class AuditService:
    def __init__(self, logs: AuditRepository) -> None:
        self._logs = logs

    def record(
        self,
        *,
        actor: User,
        action: str,
        target_type: str,
        target_id: UUID | str | None,
        summary: str,
        extra: dict | None = None,
    ) -> None:
        try:
            self._logs.create(
                actor_id=actor.id,
                actor_name=actor.name,
                actor_email=actor.email,
                action=action,
                target_type=target_type,
                target_id=str(target_id) if target_id is not None else None,
                summary=summary[:255],
                extra=extra,
            )
        except Exception:
            logger.exception("Failed to write staff audit log for %s", action)

    def list_logs(
        self,
        pagination: PaginationQuery,
        *,
        action: str | None = None,
    ) -> StaffAuditLogListResponse:
        items, total = self._logs.list_paginated(
            page=pagination.page,
            limit=pagination.limit,
            action=action,
            search=pagination.search,
        )
        return StaffAuditLogListResponse(
            message="Audit log fetched",
            data=[StaffAuditLogRead.model_validate(item) for item in items],
            meta=build_pagination_meta(total=total, page=pagination.page, limit=pagination.limit),
        )
