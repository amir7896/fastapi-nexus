from fastapi import APIRouter, Query

from app.api.deps import CurrentStockAlertStaffDep, ProductServiceDep
from app.schemas.dashboard import LowStockListResponse

router = APIRouter(prefix="/dashboard", tags=["Admin — Dashboard"])


@router.get(
    "/low-stock",
    response_model=LowStockListResponse,
    response_model_by_alias=True,
    summary="Products at or below the low-stock threshold",
)
def list_low_stock(
    _: CurrentStockAlertStaffDep,
    product_service: ProductServiceDep,
    limit: int = Query(default=8, ge=1, le=50),
) -> LowStockListResponse:
    return product_service.list_low_stock(limit=limit)
