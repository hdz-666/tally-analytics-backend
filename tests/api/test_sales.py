from datetime import date

MONTHLY_ROW = {
    "month": date(2024, 1, 1),
    "item": "Widget A",
    "stock_group": "Electronics",
    "sold_qty": 10.0,
    "sold_amount": 1000.0,
}

GROUP_ROW = {
    "month": date(2024, 1, 1),
    "stock_group": "Electronics",
    "sold_qty": 50.0,
    "sold_amount": 5000.0,
}

TOP_MOVER_ROW = {
    "item": "Widget A",
    "stock_group": "Electronics",
    "total_qty": 120.0,
    "total_amount": 12000.0,
    "months_active": 12,
}


# ── GET /api/sales/monthly ───────────────────────────────────────────────────

async def test_monthly_sales_empty(client, mock_conn):
    mock_conn.fetch.return_value = []
    response = await client.get("/api/sales/monthly")
    assert response.status_code == 200
    assert response.json() == []


async def test_monthly_sales_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [MONTHLY_ROW]
    response = await client.get("/api/sales/monthly")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["item"] == "Widget A"
    assert data[0]["sold_qty"] == 10.0
    assert data[0]["sold_amount"] == 1000.0


async def test_monthly_sales_with_item_filter(client, mock_conn):
    mock_conn.fetch.return_value = [MONTHLY_ROW]
    response = await client.get("/api/sales/monthly?item=Widget+A")
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_monthly_sales_with_date_range(client, mock_conn):
    mock_conn.fetch.return_value = [MONTHLY_ROW]
    response = await client.get(
        "/api/sales/monthly?from_date=2024-01-01&to_date=2024-12-31"
    )
    assert response.status_code == 200


async def test_monthly_sales_null_stock_group(client, mock_conn):
    row = {**MONTHLY_ROW, "stock_group": None}
    mock_conn.fetch.return_value = [row]
    response = await client.get("/api/sales/monthly")
    assert response.status_code == 200
    assert response.json()[0]["stock_group"] is None


# ── GET /api/sales/by-group ──────────────────────────────────────────────────

async def test_sales_by_group_empty(client, mock_conn):
    mock_conn.fetch.return_value = []
    assert (await client.get("/api/sales/by-group")).status_code == 200


async def test_sales_by_group_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [GROUP_ROW]
    data = (await client.get("/api/sales/by-group")).json()
    assert data[0]["stock_group"] == "Electronics"
    assert data[0]["sold_amount"] == 5000.0


async def test_sales_by_group_with_date_range(client, mock_conn):
    mock_conn.fetch.return_value = []
    response = await client.get(
        "/api/sales/by-group?from_date=2024-01-01&to_date=2024-06-30"
    )
    assert response.status_code == 200


# ── GET /api/sales/top-movers ────────────────────────────────────────────────

async def test_top_movers_default(client, mock_conn):
    mock_conn.fetch.return_value = [TOP_MOVER_ROW]
    data = (await client.get("/api/sales/top-movers")).json()
    assert data[0]["item"] == "Widget A"
    assert data[0]["months_active"] == 12


async def test_top_movers_custom_limit(client, mock_conn):
    mock_conn.fetch.return_value = []
    assert (await client.get("/api/sales/top-movers?limit=50")).status_code == 200


async def test_top_movers_with_all_filters(client, mock_conn):
    mock_conn.fetch.return_value = [TOP_MOVER_ROW]
    response = await client.get(
        "/api/sales/top-movers?limit=10&from_date=2024-01-01"
        "&to_date=2024-12-31&stock_group=Electronics"
    )
    assert response.status_code == 200


async def test_top_movers_limit_too_large_is_422(client):
    assert (await client.get("/api/sales/top-movers?limit=200")).status_code == 422


async def test_top_movers_limit_zero_is_422(client):
    assert (await client.get("/api/sales/top-movers?limit=0")).status_code == 422


# ── Auth ─────────────────────────────────────────────────────────────────────

async def test_monthly_sales_without_auth_is_403_or_401():
    """Accessing the endpoint without the dependency override should reject the request."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as unauthenticated:
        response = await unauthenticated.get("/api/sales/monthly")
    assert response.status_code in (401, 403)
