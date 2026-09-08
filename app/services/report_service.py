from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.core.exceptions import BadRequestError
from app.repositories.order_repository import OrderRepository
from app.schemas.report import ReportDayRead, ReportSummaryRead, ReportSummaryResponse

MONEY = Decimal("0.01")


class ReportService:
    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    def summary(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ReportSummaryResponse:
        start, end = _range(date_from, date_to)
        totals, sales_days, refund_days = self._orders.report_summary(start=start, end=end)
        days = _merge_days(start.date(), (end - timedelta(microseconds=1)).date(), sales_days, refund_days)
        sales = _money(totals["sales"])
        refunds = _money(totals["refunds"])
        fees = _money(totals["stripe_fees"])
        return ReportSummaryResponse(
            message="Finance report fetched",
            data=ReportSummaryRead(
                date_from=start,
                date_to=end - timedelta(microseconds=1),
                order_count=int(totals["order_count"]),
                sales=sales,
                refunds=refunds,
                stripe_fees=fees,
                net=sales - refunds - fees,
                days=days,
            ),
        )


def _range(date_from: date | None, date_to: date | None) -> tuple[datetime, datetime]:
    today = datetime.now(timezone.utc).date()
    end_date = date_to or today
    start_date = date_from or (end_date - timedelta(days=29))
    if end_date < start_date:
        raise BadRequestError("The end date must be on or after the start date")
    if (end_date - start_date).days > 366:
        raise BadRequestError("Choose a date range of 366 days or fewer")
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    return start, end


def _merge_days(
    start: date,
    end: date,
    sales_days: dict[date, dict],
    refund_days: dict[date, Decimal],
) -> list[ReportDayRead]:
    rows: list[ReportDayRead] = []
    cursor = start
    while cursor <= end:
        sales = sales_days.get(cursor, {"order_count": 0, "sales": Decimal("0"), "stripe_fees": Decimal("0")})
        refunds = refund_days.get(cursor, Decimal("0"))
        rows.append(
            ReportDayRead(
                date=cursor,
                order_count=int(sales["order_count"]),
                sales=_money(sales["sales"]),
                refunds=_money(refunds),
                stripe_fees=_money(sales["stripe_fees"]),
            )
        )
        cursor += timedelta(days=1)
    return rows


def _money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(MONEY)
