from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.services.forecasting import run_forecast
from tests.conftest import MockConnection


def sales_rows(item: str, qtys: list[float], group: str | None = "Electronics"):
    return [
        {"item": item, "stock_group": group, "month": date(2024, m + 1, 1), "sold_qty": q}
        for m, q in enumerate(qtys)
    ]


def make_conn(sales: list[dict], stock: list[dict] | None = None) -> MockConnection:
    conn = MockConnection()
    conn.fetch.side_effect = [sales, stock or []]
    return conn


@pytest.fixture
def replace_batch():
    with patch(
        "app.services.forecasting.forecast_repo.replace_forecast_batch",
        new_callable=AsyncMock,
    ) as m:
        yield m


async def test_no_sales_returns_zero(replace_batch):
    conn = make_conn([])
    assert await run_forecast(conn) == 0
    replace_batch.assert_not_called()
    assert conn.fetch.call_count == 1  # stock query skipped


async def test_items_below_min_months_are_skipped(replace_batch):
    short = sales_rows("Short", [5.0] * (settings.forecast_min_months - 1))
    conn = make_conn(short)
    assert await run_forecast(conn) == 0
    replace_batch.assert_not_called()


async def test_one_record_per_horizon_month(replace_batch):
    conn = make_conn(sales_rows("Widget A", [10.0, 12.0, 11.0, 13.0]))
    assert await run_forecast(conn, horizon_months=3) == 1

    records = replace_batch.call_args.args[1]
    assert [r["forecast_month"] for r in records] == [
        date(2024, 5, 1),
        date(2024, 6, 1),
        date(2024, 7, 1),
    ]
    assert all(r["item"] == "Widget A" for r in records)
    assert all(r["model_used"] == "trend+ema" for r in records)


async def test_forecast_months_roll_over_year(replace_batch):
    rows = [
        {"item": "X", "stock_group": "G", "month": date(2024, m, 1), "sold_qty": 5.0}
        for m in (10, 11, 12)
    ]
    conn = make_conn(rows)
    await run_forecast(conn, horizon_months=2)
    records = replace_batch.call_args.args[1]
    assert [r["forecast_month"] for r in records] == [date(2025, 1, 1), date(2025, 2, 1)]


async def test_counts_distinct_items(replace_batch):
    rows = (
        sales_rows("A", [1.0, 2.0, 3.0])
        + sales_rows("B", [4.0, 5.0, 6.0])
        + sales_rows("C", [1.0])  # too short
    )
    conn = make_conn(rows)
    assert await run_forecast(conn, horizon_months=2) == 2
    items = {r["item"] for r in replace_batch.call_args.args[1]}
    assert items == {"A", "B"}


async def test_needs_reorder_when_stock_below_reorder_point(replace_batch):
    rows = sales_rows("Low", [10.0, 10.0, 10.0]) + sales_rows("High", [10.0, 10.0, 10.0])
    stock = [
        {"name": "Low", "closing_balance": 0},
        {"name": "High", "closing_balance": 1000},
    ]
    conn = make_conn(rows, stock)
    await run_forecast(conn, horizon_months=1)
    by_item = {r["item"]: r for r in replace_batch.call_args.args[1]}

    assert by_item["Low"]["needs_reorder"] is True
    assert by_item["Low"]["current_stock"] == 0.0
    assert by_item["High"]["needs_reorder"] is False
    assert by_item["High"]["current_stock"] == 1000.0


async def test_missing_stock_treated_as_zero(replace_batch):
    conn = make_conn(sales_rows("Ghost", [3.0, 3.0, 3.0]))
    await run_forecast(conn, horizon_months=1)
    rec = replace_batch.call_args.args[1][0]
    assert rec["current_stock"] == 0.0
    assert rec["needs_reorder"] is True


async def test_constant_demand_uses_fallback_std(replace_batch):
    """Zero std over the last 6 months falls back to 20% of average demand."""
    conn = make_conn(sales_rows("Flat", [10.0] * 6))
    await run_forecast(conn, horizon_months=1)
    rec = replace_batch.call_args.args[1][0]
    expected = 10.0 * settings.lead_time_months + settings.safety_stock_z * 10.0 * 0.2
    assert rec["reorder_point"] == pytest.approx(expected, abs=1e-3)


async def test_reorder_qty_has_floor_of_one(replace_batch):
    conn = make_conn(sales_rows("Tiny", [0.0, 0.0, 0.0]))
    await run_forecast(conn, horizon_months=2)
    assert all(r["reorder_qty"] == 1.0 for r in replace_batch.call_args.args[1])


async def test_null_stock_group_becomes_empty_string(replace_batch):
    conn = make_conn(sales_rows("NoGroup", [1.0, 2.0, 3.0], group=None))
    await run_forecast(conn, horizon_months=1)
    assert replace_batch.call_args.args[1][0]["stock_group"] == ""


async def test_unsorted_input_uses_latest_month(replace_batch):
    rows = list(reversed(sales_rows("X", [1.0, 2.0, 3.0])))
    conn = make_conn(rows)
    await run_forecast(conn, horizon_months=1)
    assert replace_batch.call_args.args[1][0]["forecast_month"] == date(2024, 4, 1)
