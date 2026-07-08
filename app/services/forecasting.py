import asyncpg
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta

from app.core.config import settings
from app.repositories import forecast_repo

MIN_MONTHS_REQUIRED = settings.forecast_min_months


async def run_forecast(
    conn: asyncpg.Connection,
    horizon_months: int = settings.forecast_horizon_months,
) -> int:
    rows = await conn.fetch(
        "SELECT item, stock_group, month, sold_qty"
        " FROM v_sales_monthly ORDER BY item, month"
    )
    if not rows:
        return 0

    df = pd.DataFrame([dict(r) for r in rows])  # type: ignore[arg-type]
    df["month"] = pd.to_datetime(df["month"])
    df["sold_qty"] = df["sold_qty"].astype(float)

    stock_rows = await conn.fetch(
        "SELECT name, closing_balance FROM v_current_stock"
    )
    current_stock = {
        r["name"]: float(r["closing_balance"]) for r in stock_rows
    }

    records = []
    for item, grp in df.groupby("item"):
        grp = grp.sort_values("month")
        series = grp.set_index("month")["sold_qty"]
        stock_group = grp.iloc[0]["stock_group"] or ""

        if len(series) < MIN_MONTHS_REQUIRED:
            continue

        forecast_points = _forecast_series(
            series,
            horizon_months,
            settings.safety_stock_z,
        )

        avg_demand = float(series.tail(6).mean())
        std_demand = float(series.tail(6).std() or avg_demand * 0.2)

        # Reorder point: historical avg × lead time + safety stock (backward-looking)
        reorder_point = (
            avg_demand * settings.lead_time_months
            + settings.safety_stock_z * std_demand
        )

        # Reorder qty: avg forecasted demand × lead time (forward-looking)
        # Changes with horizon — longer horizon smooths out peaks differently
        forecast_avg = sum(pt["forecast_qty"] for pt in forecast_points) / len(forecast_points)
        reorder_qty = max(round(forecast_avg * settings.lead_time_months, 4), 1.0)
        cur_stock = current_stock.get(str(item), 0.0)

        last_month = series.index[-1].to_pydatetime().date()
        for h, pt in enumerate(forecast_points, start=1):
            fm = (last_month.replace(day=1) + relativedelta(months=h))
            records.append({
                "item": str(item),
                "stock_group": str(stock_group),
                "forecast_month": fm,
                "forecast_qty": round(pt["forecast_qty"], 4),
                "lower_bound": round(pt["lower_bound"], 4),
                "upper_bound": round(pt["upper_bound"], 4),
                "current_stock": round(cur_stock, 4),
                "reorder_point": round(reorder_point, 4),
                "reorder_qty": round(reorder_qty, 4),
                "needs_reorder": cur_stock < reorder_point,
                "model_used": "trend+ema",
            })

    if records:
        await forecast_repo.replace_forecast_batch(conn, records)

    return len({r["item"] for r in records})


def _forecast_series(
    series: pd.Series,
    horizon: int,
    z: float,
) -> list[dict]:
    values = series.values.astype(float)
    n = len(values)

    # Linear trend via least-squares
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, values, 1)

    # EMA level (alpha = 0.3)
    alpha = 0.3
    level = float(values[0])
    for v in values[1:]:
        level = alpha * v + (1 - alpha) * level

    std = float(np.std(values, ddof=1)) if n > 1 else level * 0.2

    points = []
    for h in range(1, horizon + 1):
        trend_component = slope * (n + h - 1) + intercept
        forecast = max((level + trend_component) / 2, 0.0)
        points.append({
            "forecast_qty": forecast,
            "lower_bound": max(forecast - z * std, 0.0),
            "upper_bound": forecast + z * std,
        })
    return points
