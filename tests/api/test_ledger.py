from datetime import date

HEALTH_ROW = {
    "customer": "Customer A",
    "outstanding_amount": 10000.0,
    "credit_days": 30,
    "dso_estimate": 25.0,
    "revenue_12m": 100000.0,
    "last_invoice_date": date(2024, 6, 1),
    "last_receipt_date": date(2024, 7, 1),
    "days_since_last_receipt": 15,
    "has_overdue": False,
    "total_invoices": 10,
    "total_receipts": 8,
    "total_invoiced": 50000.0,
    "total_received": 40000.0,
    "score_dso": 25.0,
    "score_overdue": 25.0,
    "score_recency": 20.0,
    "score_engagement": 15.0,
    "score_balance_ratio": 10.0,
    "health_score": 95.0,
    "health_rag": "Green",
}

PNL_ROW = {
    "month": date(2024, 1, 1),
    "revenue": 100000.0,
    "cogs": 60000.0,
    "gross_profit": 40000.0,
    "gross_margin_pct": 40.0,
    "fixed_costs": 10000.0,
    "loan_interest": 2000.0,
    "total_overhead": 12000.0,
    "net_profit": 28000.0,
    "net_margin_pct": 28.0,
}


# ── GET /api/ledger/health ───────────────────────────────────────────────────

async def test_ledger_health_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [HEALTH_ROW]
    data = (await client.get("/api/ledger/health")).json()
    assert len(data) == 1
    assert data[0]["customer"] == "Customer A"
    assert data[0]["health_score"] == 95.0
    assert data[0]["health_rag"] == "Green"
    assert data[0]["has_overdue"] is False


async def test_ledger_health_empty(client, mock_conn):
    mock_conn.fetch.return_value = []
    assert (await client.get("/api/ledger/health")).json() == []


async def test_ledger_health_optional_dates_null(client, mock_conn):
    row = {**HEALTH_ROW, "last_receipt_date": None, "dso_estimate": None}
    mock_conn.fetch.return_value = [row]
    data = (await client.get("/api/ledger/health")).json()
    assert data[0]["last_receipt_date"] is None
    assert data[0]["dso_estimate"] is None


async def test_ledger_health_overdue_customer(client, mock_conn):
    row = {**HEALTH_ROW, "has_overdue": True, "health_rag": "Red", "health_score": 30.0}
    mock_conn.fetch.return_value = [row]
    data = (await client.get("/api/ledger/health")).json()
    assert data[0]["has_overdue"] is True
    assert data[0]["health_rag"] == "Red"


# ── GET /api/ledger/pnl ──────────────────────────────────────────────────────

async def test_pnl_monthly_returns_data(client, mock_conn):
    mock_conn.fetch.return_value = [PNL_ROW]
    data = (await client.get("/api/ledger/pnl")).json()
    assert len(data) == 1
    assert data[0]["revenue"] == 100000.0
    assert data[0]["gross_profit"] == 40000.0
    assert data[0]["net_margin_pct"] == 28.0


async def test_pnl_monthly_empty(client, mock_conn):
    mock_conn.fetch.return_value = []
    assert (await client.get("/api/ledger/pnl")).json() == []


async def test_pnl_null_margins(client, mock_conn):
    """Zero-revenue month may have None margins."""
    row = {**PNL_ROW, "gross_margin_pct": None, "net_margin_pct": None, "revenue": 0.0}
    mock_conn.fetch.return_value = [row]
    data = (await client.get("/api/ledger/pnl")).json()
    assert data[0]["gross_margin_pct"] is None


# ── POST /api/ledger/refresh ─────────────────────────────────────────────────

async def test_refresh_ledger_views_success(client, mock_conn):
    """Refreshes 5 materialized views; each triggers one execute() call."""
    response = await client.post("/api/ledger/refresh")
    assert response.status_code == 200
    data = response.json()
    assert "refreshed" in data["message"].lower()
    assert mock_conn.execute.call_count == 5
