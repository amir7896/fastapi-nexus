from fastapi import APIRouter, Query

from app.api.deps import AuditServiceDep, CurrentAuditStaffDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.audit import StaffAuditLogListResponse

router = APIRouter(prefix="/audit-logs", tags=["Admin — Audit"])


@router.get(
    "",
    response_model=StaffAuditLogListResponse,
    response_model_by_alias=True,
    summary="Staff audit log",
)
def list_audit_logs(
    _: CurrentAuditStaffDep,
    audit_service: AuditServiceDep,
    page: PageQuery = 1,
    limit: LimitQuery = 20,
    search: SearchQuery = None,
    action: str | None = Query(default=None),
) -> StaffAuditLogListResponse:
    return audit_service.list_logs(build_pagination(page, limit, search), action=action)
