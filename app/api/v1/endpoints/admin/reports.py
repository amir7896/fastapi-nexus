from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import CurrentReportStaffDep, ReportServiceDep
from app.schemas.report import ReportSummaryResponse

router = APIRouter(prefix="/reports", tags=["Admin — Reports"])


@router.get(
    "/summary",
    response_model=ReportSummaryResponse,
    response_model_by_alias=True,
    summary="Date-range sales, refunds, and Stripe fees",
)
def report_summary(
    _: CurrentReportStaffDep,
    report_service: ReportServiceDep,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> ReportSummaryResponse:
    return report_service.summary(date_from=date_from, date_to=date_to)
