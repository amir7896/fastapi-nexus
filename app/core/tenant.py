from contextvars import ContextVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError

_SESSION_ORG_KEY = "organization_id"
_current_organization_id: ContextVar[UUID | None] = ContextVar(
    "current_organization_id",
    default=None,
)


def set_current_organization_id(organization_id: UUID | None, db: Session | None = None) -> None:
    _current_organization_id.set(organization_id)
    if db is not None:
        db.info[_SESSION_ORG_KEY] = organization_id


def get_current_organization_id(db: Session | None = None) -> UUID | None:
    if db is not None and _SESSION_ORG_KEY in db.info:
        return db.info.get(_SESSION_ORG_KEY)
    return _current_organization_id.get()


def require_organization_id(db: Session | None = None) -> UUID:
    org_id = get_current_organization_id(db)
    if org_id is None:
        raise ForbiddenError("No active store")
    return org_id


def organization_clause(column, db: Session | None = None):
    org_id = get_current_organization_id(db)
    if org_id is None:
        return None
    return column == org_id


def apply_organization_filter(filters: list, column, db: Session | None = None) -> list:
    clause = organization_clause(column, db)
    if clause is not None:
        filters.append(clause)
    return filters


def visible_in_organization(entity, db: Session | None = None) -> bool:
    org_id = get_current_organization_id(db)
    if org_id is None:
        return True
    entity_org = getattr(entity, "organization_id", None)
    if entity_org is None:
        return True
    return entity_org == org_id
