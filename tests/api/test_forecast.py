from datetime import date
from unittest.mock import AsyncMock, patch

FORECAST_ROW = {
    "item": "Widget A",
    "stock_group": "Electronics",
    "forecast_month": date(2024, 7, 1),
    "forecast_qty": 12.5,
    "lower_bound": 8.0,
    "upper_bound": 17.0,
}

REORDER_ROW = {
    "item": "Widget B",
    "stock_group": "Electronics",
    "current_stock": 5.0,
    "reorder_point": 20.0,
    "reorder_qty": 40.0,
    "needs_reorder": True,
}


# ── GET /api/forecast/items ──────────────────────────────────────────────────

async def test_get_forecast_all_items(client, mock_conn):
    mock_conn.fetch.return_value = [FORECAST_ROW]
    data = (await client.get("/api/forecast/items")).json()
    assert data[0]["item"] == "Widget A"
    assert data[0]["forecast_qty"] == 12.5
    assert data[0]["lower_bound"] == 8.0


async def test_get_forecast_empty(client, mock_conn):
    mock_conn.fetch.return_value = []
    assert (await client.get("/api/forecast/items")).json() == []


async def test_get_forecast_with_item_filter(client, mock_conn):
    mock_conn.fetch.return_value = [FORECAST_ROW]
    response = await client.get("/api/forecast/items?item=Widget+A")
    assert response.status_code == 200
    assert response.json()[0]["item"] == "Widget A"


async def test_get_forecast_optional_stock_group(client, mock_conn):
    row = {**FORECAST_ROW, "stock_group": None}
    mock_conn.fetch.return_value = [row]
    data = (await client.get("/api/forecast/items")).json()
    assert data[0]["stock_group"] is None


# ── GET /api/forecast/reorder-alerts ────────────────────────────────────────

async def test_reorder_alerts_needs_reorder(client, mock_conn):
    mock_conn.fetch.return_value = [REORDER_ROW]
    data = (await client.get("/api/forecast/reorder-alerts")).json()
    assert data[0]["needs_reorder"] is True
    assert data[0]["current_stock"] == 5.0
    assert data[0]["reorder_point"] == 20.0


async def test_reorder_alerts_empty(client, mock_conn):
    mock_conn.fetch.return_value = []
    assert (await client.get("/api/forecast/reorder-alerts")).json() == []


async def test_reorder_alerts_no_reorder_needed(client, mock_conn):
    row = {**REORDER_ROW, "current_stock": 100.0, "needs_reorder": False}
    mock_conn.fetch.return_value = [row]
    data = (await client.get("/api/forecast/reorder-alerts")).json()
    assert data[0]["needs_reorder"] is False


# ── POST /api/forecast/run ───────────────────────────────────────────────────

async def test_run_forecast_default_horizon(client, mock_conn):
    with patch("app.services.forecasting.run_forecast", AsyncMock(return_value=5)):
        response = await client.post("/api/forecast/run")
    assert response.status_code == 200
    data = response.json()
    assert data["items_processed"] == 5
    assert "6-month" in data["message"]


async def test_run_forecast_custom_horizon(client, mock_conn):
    with patch("app.services.forecasting.run_forecast", AsyncMock(return_value=3)):
        response = await client.post("/api/forecast/run?horizon_months=12")
    assert response.status_code == 200
    assert "12-month" in response.json()["message"]


async def test_run_forecast_zero_items(client, mock_conn):
    with patch("app.services.forecasting.run_forecast", AsyncMock(return_value=0)):
        response = await client.post("/api/forecast/run")
    assert response.json()["items_processed"] == 0


async def test_run_forecast_horizon_too_large_is_422(client):
    assert (await client.post("/api/forecast/run?horizon_months=25")).status_code == 422


async def test_run_forecast_horizon_too_small_is_422(client):
    assert (await client.post("/api/forecast/run?horizon_months=0")).status_code == 422
