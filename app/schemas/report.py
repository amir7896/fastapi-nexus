from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ReportDayRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date: date
    order_count: int = Field(serialization_alias="orderCount")
    sales: Decimal
    refunds: Decimal
    stripe_fees: Decimal = Field(serialization_alias="stripeFees")


class ReportSummaryRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date_from: datetime = Field(serialization_alias="from")
    date_to: datetime = Field(serialization_alias="to")
    order_count: int = Field(serialization_alias="orderCount")
    sales: Decimal
    refunds: Decimal
    stripe_fees: Decimal = Field(serialization_alias="stripeFees")
    net: Decimal
    days: list[ReportDayRead]


class ReportSummaryResponse(BaseModel):
    message: str
    data: ReportSummaryRead
