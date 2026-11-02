from datetime import date

AREA_ROW = {
    "area": "Indore",
    "lat": 22.72,
    "lon": 75.86,
    "state": "Madhya Pradesh",
    "resolution_level": "pincode",
    "sold_qty": 120.0,
    "sold_amount": 54000.0,
    "client_count": 7,
}

CLIENT_ROW = {
    "party_name": "Sharma Traders",
    "sold_qty": 40.0,
    "sold_amount": 18000.0,
    "item_count": 5,
}

PINCODE_ROW = {
    "pincode": "452001",
    "area": "Indore",
    "state": "Madhya Pradesh",
    "lat": 22.72,
    "lon": 75.86,
    "sold_qty": 60.0,
    "sold_amount": 27000.0,
    "client_count": 3,
}

CLIENT_ITEM_ROW = {
    "item": "Widget A",
    "stock_group": "Electronics",
    "sold_qty": 10.0,
    "sold_amount": 4500.0,
}


def last_query(mock_conn):
    """Return (sql, args) of the most recent conn.fetch call."""
    call = mock_conn.fetch.call_args
    return call.args[0], list(call.args[1:])


# ── GET /api/sales/by-area ───────────────────────────────────────────────────

async def test_by_area_empty(client, mock_conn):
    mock_conn.fetch.return_value = []
    response = await client.get("/api/sales/by-area")
    assert response.status_code == 200
    assert response.json() == []


async def test_by_area_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [AREA_ROW]
    data = (await client.get("/api/sales/by-area")).json()
    assert data[0]["area"] == "Indore"
    assert data[0]["client_count"] == 7
    assert data[0]["resolution_level"] == "pincode"


async def test_by_area_no_filters_has_no_where(client, mock_conn):
    await client.get("/api/sales/by-area")
    sql, args = last_query(mock_conn)
    assert "WHERE month" not in sql
    assert args == []


async def test_by_area_all_filters_bound_in_order(client, mock_conn):
    await client.get(
        "/api/sales/by-area?from_date=2024-01-01&to_date=2024-12-31"
        "&item=Widget+A&stock_group=Electronics&stock_group=Tools&pincode=452001"
    )
    sql, args = last_query(mock_conn)
    assert args == [
        date(2024, 1, 1),
        date(2024, 12, 31),
        "Widget A",
        ["Electronics", "Tools"],
        "452001",
    ]
    assert "month >= $1" in sql
    assert "month <= $2" in sql
    assert "item = $3" in sql
    assert "stock_group = ANY($4)" in sql
    assert "pincode = $5" in sql


async def test_by_area_null_state_allowed(client, mock_conn):
    mock_conn.fetch.return_value = [{**AREA_ROW, "state": None}]
    response = await client.get("/api/sales/by-area")
    assert response.status_code == 200
    assert response.json()[0]["state"] is None


async def test_by_area_invalid_date_is_422(client):
    assert (await client.get("/api/sales/by-area?from_date=not-a-date")).status_code == 422


# ── GET /api/sales/by-area/{area}/clients ────────────────────────────────────

async def test_area_clients_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [CLIENT_ROW]
    data = (await client.get("/api/sales/by-area/Indore/clients")).json()
    assert data[0]["party_name"] == "Sharma Traders"
    assert data[0]["item_count"] == 5


async def test_area_clients_area_is_first_param(client, mock_conn):
    await client.get("/api/sales/by-area/Indore/clients?item=Widget+A&pincode=452001")
    sql, args = last_query(mock_conn)
    assert args == ["Indore", "Widget A", "452001"]
    assert "area = $1" in sql
    assert "item = $2" in sql
    assert "pincode = $3" in sql


async def test_area_clients_url_encoded_area(client, mock_conn):
    await client.get("/api/sales/by-area/New%20Delhi/clients")
    _, args = last_query(mock_conn)
    assert args == ["New Delhi"]


# ── GET /api/sales/by-area/{area}/pincodes ───────────────────────────────────

async def test_area_pincodes_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [PINCODE_ROW]
    data = (await client.get("/api/sales/by-area/Indore/pincodes")).json()
    assert data[0]["pincode"] == "452001"
    assert data[0]["sold_amount"] == 27000.0


async def test_area_pincodes_excludes_null_pincodes(client, mock_conn):
    await client.get(
        "/api/sales/by-area/Indore/pincodes?from_date=2024-01-01&stock_group=Tools"
    )
    sql, args = last_query(mock_conn)
    assert "pincode IS NOT NULL" in sql
    assert args == ["Indore", date(2024, 1, 1), ["Tools"]]
    assert "stock_group = ANY($3)" in sql


# ── GET /api/sales/clients/{party_name}/items ────────────────────────────────

async def test_client_items_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [CLIENT_ITEM_ROW]
    data = (await client.get("/api/sales/clients/Sharma%20Traders/items")).json()
    assert data[0]["item"] == "Widget A"
    assert data[0]["sold_amount"] == 4500.0


async def test_client_items_date_filters(client, mock_conn):
    await client.get(
        "/api/sales/clients/Sharma%20Traders/items?from_date=2024-01-01&to_date=2024-06-30"
    )
    sql, args = last_query(mock_conn)
    assert args == ["Sharma Traders", date(2024, 1, 1), date(2024, 6, 30)]
    assert "party_name = $1" in sql
    assert "month >= $2" in sql
    assert "month <= $3" in sql


async def test_client_items_null_stock_group(client, mock_conn):
    mock_conn.fetch.return_value = [{**CLIENT_ITEM_ROW, "stock_group": None}]
    assert (await client.get("/api/sales/clients/X/items")).json()[0]["stock_group"] is None


# ── GET /api/sales/pincodes ──────────────────────────────────────────────────

async def test_pincodes_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [PINCODE_ROW]
    data = (await client.get("/api/sales/pincodes")).json()
    assert data[0]["area"] == "Indore"


async def test_pincodes_without_filters_only_requires_pincode(client, mock_conn):
    await client.get("/api/sales/pincodes")
    sql, args = last_query(mock_conn)
    assert "WHERE pincode IS NOT NULL" in sql
    assert args == []


async def test_pincodes_item_filter(client, mock_conn):
    await client.get("/api/sales/pincodes?item=Widget+A")
    sql, args = last_query(mock_conn)
    assert args == ["Widget A"]
    assert "item = $1" in sql


# ── Response validation ──────────────────────────────────────────────────────

async def test_by_area_missing_required_field_is_error(client, mock_conn):
    """A row missing lat/lon must not be silently returned."""
    bad = {k: v for k, v in AREA_ROW.items() if k != "lat"}
    mock_conn.fetch.return_value = [bad]
    try:
        response = await client.get("/api/sales/by-area")
    except Exception:
        return  # validation error propagated — acceptable
    assert response.status_code >= 500
