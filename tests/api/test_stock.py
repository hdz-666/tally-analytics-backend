STOCK_ITEM_ROW = {
    "name": "Widget A",
    "stock_group": "Electronics",
    "closing_balance": 100.0,
    "closing_value": 5000.0,
    "closing_rate": 50.0,
}

SUMMARY_ROW = {
    "total_items": 50,
    "total_value": 100000.0,
    "low_stock_count": 5,
    "out_of_stock_count": 2,
}


# ── GET /api/stock/items ─────────────────────────────────────────────────────

async def test_list_items_all(client, mock_conn):
    mock_conn.fetch.return_value = [STOCK_ITEM_ROW]
    data = (await client.get("/api/stock/items")).json()
    assert data[0]["name"] == "Widget A"
    assert data[0]["closing_balance"] == 100.0


async def test_list_items_empty(client, mock_conn):
    mock_conn.fetch.return_value = []
    assert (await client.get("/api/stock/items")).json() == []


async def test_list_items_with_group_no_hierarchy_table(client, mock_conn):
    """When _group_table returns None → falls back to simple WHERE stock_group = ?"""
    mock_conn.fetchrow.return_value = None
    mock_conn.fetch.return_value = [STOCK_ITEM_ROW]
    data = (await client.get("/api/stock/items?group=Electronics")).json()
    assert data[0]["name"] == "Widget A"


async def test_list_items_with_group_with_hierarchy_table(client, mock_conn):
    """When a group table is found → uses recursive CTE."""
    mock_conn.fetchrow.return_value = {"table_name": "mst_stock_group"}
    mock_conn.fetch.return_value = [STOCK_ITEM_ROW]
    response = await client.get("/api/stock/items?group=Electronics")
    assert response.status_code == 200


async def test_list_items_null_stock_group(client, mock_conn):
    row = {**STOCK_ITEM_ROW, "stock_group": None}
    mock_conn.fetch.return_value = [row]
    data = (await client.get("/api/stock/items")).json()
    assert data[0]["stock_group"] is None


# ── GET /api/stock/groups ────────────────────────────────────────────────────

async def test_list_groups_fallback_no_table(client, mock_conn):
    """No hierarchy table → derive from distinct stock_group values in v_current_stock."""
    mock_conn.fetchrow.return_value = None
    mock_conn.fetch.return_value = [{"name": "Electronics"}]
    data = (await client.get("/api/stock/groups")).json()
    assert data[0]["name"] == "Electronics"
    assert data[0]["parent"] is None


async def test_list_groups_with_hierarchy_table(client, mock_conn):
    mock_conn.fetchrow.return_value = {"table_name": "mst_stock_group"}
    mock_conn.fetch.return_value = [
        {"name": "Electronics", "parent": None},
        {"name": "Phones", "parent": "Electronics"},
    ]
    data = (await client.get("/api/stock/groups")).json()
    assert len(data) == 2
    assert data[1]["parent"] == "Electronics"


async def test_list_groups_empty(client, mock_conn):
    mock_conn.fetchrow.return_value = None
    mock_conn.fetch.return_value = []
    assert (await client.get("/api/stock/groups")).json() == []


# ── GET /api/stock/summary ───────────────────────────────────────────────────

async def test_summary_returns_correct_fields(client, mock_conn):
    mock_conn.fetchrow.return_value = SUMMARY_ROW
    data = (await client.get("/api/stock/summary")).json()
    assert data["total_items"] == 50
    assert data["total_value"] == 100000.0
    assert data["low_stock_count"] == 5
    assert data["out_of_stock_count"] == 2


async def test_summary_all_zeros(client, mock_conn):
    mock_conn.fetchrow.return_value = {
        "total_items": 0,
        "total_value": 0.0,
        "low_stock_count": 0,
        "out_of_stock_count": 0,
    }
    data = (await client.get("/api/stock/summary")).json()
    assert data["total_items"] == 0


# ── GET /api/stock/debug/tables ──────────────────────────────────────────────

async def test_debug_tables_returns_name_list(client, mock_conn):
    mock_conn.fetch.return_value = [
        {"table_name": "mst_stock_item"},
        {"table_name": "trn_voucher"},
    ]
    data = (await client.get("/api/stock/debug/tables")).json()
    assert "mst_stock_item" in data
    assert "trn_voucher" in data


async def test_debug_tables_empty_schema(client, mock_conn):
    mock_conn.fetch.return_value = []
    assert (await client.get("/api/stock/debug/tables")).json() == []
