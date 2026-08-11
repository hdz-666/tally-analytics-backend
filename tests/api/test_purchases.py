from datetime import date

PURCHASE_ROW = {
    "stock_group": "Electronics",
    "month": date(2024, 1, 1),
    "purchase_qty": 200.0,
    "purchase_amount": 20000.0,
}


# ── GET /api/purchases/by-group ──────────────────────────────────────────────

async def test_purchases_by_group_empty(client, mock_conn):
    mock_conn.fetch.return_value = []
    response = await client.get("/api/purchases/by-group")
    assert response.status_code == 200
    assert response.json() == []


async def test_purchases_by_group_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [PURCHASE_ROW]
    data = (await client.get("/api/purchases/by-group")).json()
    assert len(data) == 1
    assert data[0]["stock_group"] == "Electronics"
    assert data[0]["purchase_amount"] == 20000.0


async def test_purchases_with_from_date(client, mock_conn):
    mock_conn.fetch.return_value = []
    response = await client.get("/api/purchases/by-group?from_date=2024-01-01")
    assert response.status_code == 200


async def test_purchases_with_to_date(client, mock_conn):
    mock_conn.fetch.return_value = []
    response = await client.get("/api/purchases/by-group?to_date=2024-12-31")
    assert response.status_code == 200


async def test_purchases_with_date_range(client, mock_conn):
    mock_conn.fetch.return_value = [PURCHASE_ROW]
    response = await client.get(
        "/api/purchases/by-group?from_date=2024-01-01&to_date=2024-06-30"
    )
    assert response.status_code == 200


async def test_purchases_invalid_from_date_is_422(client):
    response = await client.get("/api/purchases/by-group?from_date=not-a-date")
    assert response.status_code == 422


async def test_purchases_multiple_groups(client, mock_conn):
    rows = [
        {**PURCHASE_ROW, "stock_group": "Electronics"},
        {**PURCHASE_ROW, "stock_group": "Hardware", "purchase_amount": 5000.0},
    ]
    mock_conn.fetch.return_value = rows
    data = (await client.get("/api/purchases/by-group")).json()
    assert len(data) == 2
    groups = {r["stock_group"] for r in data}
    assert "Electronics" in groups
    assert "Hardware" in groups
