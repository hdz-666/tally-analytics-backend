import asyncpg
from app.schemas.ledger import LedgerHealthSchema, PnlMonthlySchema


async def get_ledger_health(conn: asyncpg.Connection) -> list[LedgerHealthSchema]:
    rows = await conn.fetch(
        "SELECT * FROM tallypnl.v_b_ledger_health ORDER BY health_score ASC"
    )
    return [LedgerHealthSchema(**dict(r)) for r in rows]


async def get_pnl_monthly(conn: asyncpg.Connection) -> list[PnlMonthlySchema]:
    rows = await conn.fetch(
        "SELECT * FROM tallypnl.v_pnl_monthly ORDER BY month"
    )
    return [PnlMonthlySchema(**dict(r)) for r in rows]


async def refresh_views(conn: asyncpg.Connection) -> None:
    for view in [
        "tallypnl.v_b_sales_monthly",
        "tallypnl.v_b_customer_outstanding",
        "tallypnl.v_b_invoice_activity",
        "tallypnl.v_b_ledger_summary",
        "tallypnl.v_b_ledger_health",
    ]:
        await conn.execute(f"REFRESH MATERIALIZED VIEW {view}")
