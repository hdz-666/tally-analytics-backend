from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import (
    ADMIN,
    COMPANY_EXEC,
    EXECUTIVE,
    Principal,
    get_current_user,
)
from app.core.database import get_conn
from app.main import app
from tests.conftest import MOCK_USER


def principal_for(role: str, groups: tuple[str, ...] | None = None):
    return Principal(
        id="test-user-id",
        email="test@example.com",
        role=role,
        categories=("Gloirio",) if role == COMPANY_EXEC else (),
        allowed_groups=groups if role == COMPANY_EXEC else None,
    )


# Endpoint → roles allowed to reach it. Anything not listed gets a 403.
ACCESS = [
    ("GET", "/api/stock/items", {ADMIN, EXECUTIVE, COMPANY_EXEC}),
    ("GET", "/api/stock/groups", {ADMIN, EXECUTIVE, COMPANY_EXEC}),
    ("GET", "/api/stock/summary", {ADMIN, EXECUTIVE}),
    ("GET", "/api/stock/debug/tables", {ADMIN}),
    ("GET", "/api/sales/monthly", {ADMIN, EXECUTIVE, COMPANY_EXEC}),
    ("GET", "/api/sales/by-group", {ADMIN, EXECUTIVE, COMPANY_EXEC}),
    ("GET", "/api/sales/top-movers", {ADMIN, EXECUTIVE, COMPANY_EXEC}),
    ("GET", "/api/sales/by-area", {ADMIN, EXECUTIVE, COMPANY_EXEC}),
    ("GET", "/api/sales/pincodes", {ADMIN, EXECUTIVE, COMPANY_EXEC}),
    ("GET", "/api/sales/clients/Acme/items",
     {ADMIN, EXECUTIVE, COMPANY_EXEC}),
    ("GET", "/api/forecast/reorder-alerts", {ADMIN, EXECUTIVE}),
    ("GET", "/api/forecast/items", {ADMIN}),
    ("POST", "/api/forecast/run", {ADMIN}),
    ("GET", "/api/purchases/by-group", {ADMIN}),
    ("GET", "/api/ledger/pnl", {ADMIN}),
    ("POST", "/api/ledger/refresh", {ADMIN}),
    ("GET", "/api/users", {ADMIN}),
    ("GET", "/api/me", {ADMIN, EXECUTIVE, COMPANY_EXEC}),
]


@pytest.mark.parametrize("role", [ADMIN, EXECUTIVE, COMPANY_EXEC])
@pytest.mark.parametrize("method,path,allowed", ACCESS)
async def test_access_matrix(
    client, mock_conn, as_principal, mocker, role, method, path, allowed
):
    as_principal(principal_for(role, groups=("Gloirio",)))
    # One row that satisfies every fetchrow-based endpoint in the matrix.
    mock_conn.fetchrow.return_value = {
        "table_name": "mst_stock_group",
        "total_items": 0, "total_value": 0.0,
        "low_stock_count": 0, "out_of_stock_count": 0,
        "total_overdue": 0, "total_outstanding": 0, "pct_overdue": 0,
        "bucket_0_30": 0, "bucket_31_60": 0, "bucket_61_90": 0,
        "bucket_over_90": 0,
    }
    mocker.patch(
        "app.routers.forecast.forecasting.run_forecast", return_value=0
    )
    response = await client.request(method, path)
    if role in allowed:
        assert response.status_code != 403, response.text
    else:
        assert response.status_code == 403


# ── company exec scoping ─────────────────────────────────────────────────────

def last_query_args(mock_conn):
    call = mock_conn.fetch.call_args
    return call.args[0], list(call.args[1:])


@pytest.mark.parametrize("path", [
    "/api/sales/monthly",
    "/api/sales/by-group",
    "/api/sales/top-movers",
    "/api/sales/by-area",
    "/api/sales/pincodes",
    "/api/sales/by-area/Pune/clients",
    "/api/sales/by-area/Pune/pincodes",
    "/api/sales/clients/Acme/items",
])
async def test_company_exec_sales_are_scoped(
    client, mock_conn, as_principal, path
):
    as_principal(principal_for(COMPANY_EXEC, groups=("Gloirio", "G-Kids")))
    assert (await client.get(path)).status_code == 200
    sql, args = last_query_args(mock_conn)
    assert "stock_group = ANY(" in sql
    assert ["Gloirio", "G-Kids"] in args


async def test_company_exec_cannot_widen_scope_with_filter(
    client, mock_conn, as_principal
):
    """A stock_group filter for someone else's brand is ANDed with the
    scope, so the query still can't return rows outside it."""
    as_principal(principal_for(COMPANY_EXEC, groups=("Gloirio",)))
    await client.get("/api/sales/by-area?stock_group=Trend")
    sql, args = last_query_args(mock_conn)
    assert sql.count("stock_group = ANY(") == 2
    assert ["Trend"] in args and ["Gloirio"] in args


async def test_company_exec_without_groups_sees_nothing(
    client, mock_conn, as_principal
):
    as_principal(principal_for(COMPANY_EXEC, groups=()))
    await client.get("/api/sales/monthly")
    sql, args = last_query_args(mock_conn)
    assert "stock_group = ANY(" in sql
    assert [] in args


@pytest.mark.parametrize("role", [ADMIN, EXECUTIVE])
async def test_staff_sales_are_unscoped(client, mock_conn, as_principal, role):
    as_principal(principal_for(role))
    await client.get("/api/sales/monthly")
    sql, _ = last_query_args(mock_conn)
    assert "stock_group" not in sql


async def test_staff_top_movers_use_precomputed_view(
    client, mock_conn, as_principal
):
    as_principal(principal_for(EXECUTIVE))
    await client.get("/api/sales/top-movers")
    sql, _ = last_query_args(mock_conn)
    assert "v_top_moving_items" in sql


STOCK_ROWS = [
    {"name": "Gloirio Tee", "stock_group": "G-Kids", "closing_balance": 5.0,
     "closing_value": 500.0, "closing_rate": 100.0},
    {"name": "Trend Cap", "stock_group": "Trend", "closing_balance": 9.0,
     "closing_value": 900.0, "closing_rate": 100.0},
    {"name": "Loose", "stock_group": None, "closing_balance": 1.0,
     "closing_value": 10.0, "closing_rate": 10.0},
]


async def test_company_exec_stock_items_filtered_and_stripped(
    client, mock_conn, as_principal
):
    as_principal(principal_for(COMPANY_EXEC, groups=("Gloirio", "G-Kids")))
    mock_conn.fetch.return_value = STOCK_ROWS
    data = (await client.get("/api/stock/items")).json()
    assert data == [{
        "name": "Gloirio Tee", "stock_group": "G-Kids",
        "closing_balance": 5.0, "closing_value": None, "closing_rate": None,
    }]


async def test_executive_stock_items_keep_value_and_rate(
    client, mock_conn, as_principal
):
    as_principal(principal_for(EXECUTIVE))
    mock_conn.fetch.return_value = STOCK_ROWS
    data = (await client.get("/api/stock/items")).json()
    assert len(data) == 3
    assert data[0]["closing_rate"] == 100.0


async def test_company_exec_groups_filtered_with_roots_detached(
    client, mock_conn, as_principal
):
    as_principal(principal_for(COMPANY_EXEC, groups=("Gloirio", "G-Kids")))
    mock_conn.fetchrow.return_value = {"table_name": "mst_stock_group"}
    mock_conn.fetch.return_value = [
        {"name": "Brands", "parent": None},
        {"name": "Gloirio", "parent": "Brands"},
        {"name": "G-Kids", "parent": "Gloirio"},
        {"name": "Trend", "parent": "Brands"},
    ]
    data = (await client.get("/api/stock/groups")).json()
    assert data == [
        {"name": "Gloirio", "parent": None},
        {"name": "G-Kids", "parent": "Gloirio"},
    ]


# ── real get_principal + route share no pool checkout ───────────────────────

class SingleUseConn:
    """Mimics asyncpg's PoolAcquireContext: entering it twice raises."""

    def __init__(self, role=ADMIN):
        self.used = False
        self.fetch = AsyncMock(return_value=[])
        self.fetchval = AsyncMock(return_value=role)

    async def __aenter__(self):
        if self.used:
            raise RuntimeError("a connection is already acquired")
        self.used = True
        return self

    async def __aexit__(self, *args):
        return False


async def test_principal_and_route_use_separate_connections(mocker):
    """Regression: get_principal once took its connection via
    Depends(get_conn, use_cache=False), and FastAPI still handed that same
    checkout to the route, which blew up on the second `async with`."""
    mocker.patch(
        "app.core.auth.get_conn", AsyncMock(side_effect=SingleUseConn)
    )
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_conn] = SingleUseConn
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as ac:
            response = await ac.get("/api/users")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
