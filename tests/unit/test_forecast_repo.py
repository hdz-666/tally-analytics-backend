from datetime import date

from app.repositories.forecast_repo import replace_forecast_batch
from tests.conftest import MockConnection

RECORD = {
    "item": "Widget A",
    "stock_group": "Electronics",
    "forecast_month": date(2024, 7, 1),
    "forecast_qty": 12.5,
    "lower_bound": 8.0,
    "upper_bound": 17.0,
    "current_stock": 5.0,
    "reorder_point": 20.0,
    "reorder_qty": 40.0,
    "needs_reorder": True,
    "model_used": "trend+ema",
}


async def test_empty_batch_is_noop():
    conn = MockConnection()
    await replace_forecast_batch(conn, [])
    conn.execute.assert_not_called()
    conn.copy_records_to_table.assert_not_called()


async def test_deletes_existing_rows_for_items():
    conn = MockConnection()
    records = [RECORD, {**RECORD, "forecast_month": date(2024, 8, 1)}, {**RECORD, "item": "B"}]
    await replace_forecast_batch(conn, records)

    sql, items = conn.execute.call_args.args
    assert sql.startswith("DELETE FROM stock_forecast")
    assert sorted(items) == ["B", "Widget A"]


async def test_copies_records_in_column_order():
    conn = MockConnection()
    await replace_forecast_batch(conn, [RECORD])

    call = conn.copy_records_to_table.call_args
    assert call.args[0] == "stock_forecast"
    columns = call.kwargs["columns"]
    (row,) = call.kwargs["records"]
    assert dict(zip(columns, row)) == RECORD
