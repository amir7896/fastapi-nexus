from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.audit import StaffAuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        actor_id: UUID | None,
        actor_name: str,
        actor_email: str,
        action: str,
        target_type: str,
        target_id: str | None,
        summary: str,
        extra: dict | None = None,
    ) -> StaffAuditLog:
        entry = StaffAuditLog(
            actor_id=actor_id,
            actor_name=actor_name,
            actor_email=actor_email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=summary,
            extra=extra,
        )
        self._db.add(entry)
        self._db.commit()
        self._db.refresh(entry)
        return entry

    def list_paginated(
        self,
        *,
        page: int,
        limit: int,
        action: str | None = None,
        search: str | None = None,
    ) -> tuple[list[StaffAuditLog], int]:
        filters = []
        if action:
            filters.append(StaffAuditLog.action == action)
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    StaffAuditLog.actor_name.ilike(pattern),
                    StaffAuditLog.actor_email.ilike(pattern),
                    StaffAuditLog.summary.ilike(pattern),
                    StaffAuditLog.action.ilike(pattern),
                )
            )
        count_stmt = select(func.count(StaffAuditLog.id))
        list_stmt = select(StaffAuditLog).order_by(StaffAuditLog.created_at.desc())
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)
        total = self._db.scalar(count_stmt) or 0
        offset = (page - 1) * limit
        items = list(self._db.scalars(list_stmt.offset(offset).limit(limit)).all())
        return items, total
