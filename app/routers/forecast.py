from fastapi import APIRouter, Depends, Query
import asyncpg

from app.core.database import get_conn
from app.repositories import forecast_repo
from app.services import forecasting
from app.schemas.forecast import (
    ForecastPointSchema,
    ReorderAlertSchema,
    ForecastRunResponseSchema,
)

router = APIRouter()


@router.get("/items", response_model=list[ForecastPointSchema])
async def get_forecast(
    item: str | None = None,
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await forecast_repo.get_forecast(c, item)


@router.get("/reorder-alerts", response_model=list[ReorderAlertSchema])
async def reorder_alerts(conn: asyncpg.Connection = Depends(get_conn)):
    async with conn as c:
        return await forecast_repo.get_reorder_alerts(c)


@router.post("/run", response_model=ForecastRunResponseSchema)
async def run_forecast(
    horizon_months: int = Query(default=6, ge=1, le=24),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        count = await forecasting.run_forecast(c, horizon_months=horizon_months)
    return ForecastRunResponseSchema(
        items_processed=count,
        message=f"Forecast complete for {count} items "
                f"({horizon_months}-month horizon).",
    )
