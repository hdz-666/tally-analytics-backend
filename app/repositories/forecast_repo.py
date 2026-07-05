import asyncpg
from app.schemas.forecast import ForecastPointSchema, ReorderAlertSchema


async def get_forecast(
    conn: asyncpg.Connection, item: str | None = None
) -> list[ForecastPointSchema]:
    if item:
        rows = await conn.fetch(
            "SELECT * FROM stock_forecast WHERE item = $1 ORDER BY forecast_month",
            item,
        )
    else:
        rows = await conn.fetch(
            "SELECT * FROM stock_forecast ORDER BY item, forecast_month"
        )
    return [ForecastPointSchema(**dict(r)) for r in rows]


async def get_reorder_alerts(conn: asyncpg.Connection) -> list[ReorderAlertSchema]:
    rows = await conn.fetch(
        "SELECT * FROM v_reorder_alerts ORDER BY needs_reorder DESC, item"
    )
    return [ReorderAlertSchema(**dict(r)) for r in rows]


async def replace_forecast_batch(
    conn: asyncpg.Connection, records: list[dict]
) -> None:
    if not records:
        return

    items: list[str] = list({r["item"] for r in records})  # type: ignore[misc]

    async with conn.transaction():  # type: ignore[attr-defined]
        # Delete all existing forecasts for these items so old horizon data is gone
        await conn.execute(  # type: ignore[attr-defined]
            "DELETE FROM stock_forecast WHERE item = ANY($1::text[])", items
        )
        await conn.copy_records_to_table(  # type: ignore[attr-defined]
            "stock_forecast",
            records=[
                (
                    r["item"], r["stock_group"], r["forecast_month"],
                    r["forecast_qty"], r["lower_bound"], r["upper_bound"],
                    r["current_stock"], r["reorder_point"], r["reorder_qty"],
                    r["needs_reorder"], r["model_used"],
                )
                for r in records
            ],
            columns=[
                "item", "stock_group", "forecast_month",
                "forecast_qty", "lower_bound", "upper_bound",
                "current_stock", "reorder_point", "reorder_qty",
                "needs_reorder", "model_used",
            ],
        )
