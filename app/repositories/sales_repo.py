import asyncpg
from datetime import date
from app.schemas.sales import (
    MonthlySalesSchema,
    GroupSalesSchema,
    TopMoverSchema,
)


async def get_monthly_sales(
    conn: asyncpg.Connection,
    item: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[MonthlySalesSchema]:
    conditions = []
    args: list = []

    if item:
        args.append(item)
        conditions.append(f"item = ${len(args)}")
    if from_date:
        args.append(from_date)
        conditions.append(f"month >= ${len(args)}")
    if to_date:
        args.append(to_date)
        conditions.append(f"month <= ${len(args)}")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = await conn.fetch(
        f"SELECT * FROM v_sales_monthly {where} ORDER BY item, month", *args
    )
    return [MonthlySalesSchema(**dict(r)) for r in rows]


async def get_sales_by_group(
    conn: asyncpg.Connection,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[GroupSalesSchema]:
    conditions = []
    args: list = []

    if from_date:
        args.append(from_date)
        conditions.append(f"month >= ${len(args)}")
    if to_date:
        args.append(to_date)
        conditions.append(f"month <= ${len(args)}")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = await conn.fetch(
        f"SELECT * FROM v_sales_by_group {where}"
        " ORDER BY stock_group, month",
        *args
    )
    return [GroupSalesSchema(**dict(r)) for r in rows]


async def get_top_movers(
    conn: asyncpg.Connection,
    limit: int = 20,
    from_date: date | None = None,
    to_date: date | None = None,
    stock_group: str | None = None,
) -> list[TopMoverSchema]:
    if from_date or to_date or stock_group:
        conditions: list[str] = []
        args: list = [limit]
        if from_date:
            args.append(from_date)
            conditions.append(f"month >= ${len(args)}")
        if to_date:
            args.append(to_date)
            conditions.append(f"month <= ${len(args)}")
        if stock_group:
            args.append(stock_group)
            conditions.append(f"stock_group = ${len(args)}")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = await conn.fetch(
            f"""
            SELECT item, stock_group,
                   SUM(sold_qty)         AS total_qty,
                   SUM(sold_amount)      AS total_amount,
                   COUNT(DISTINCT month) AS months_active
            FROM v_sales_monthly
            {where}
            GROUP BY item, stock_group
            ORDER BY total_amount DESC
            LIMIT $1
            """,
            *args,
        )
    else:
        rows = await conn.fetch(
            "SELECT * FROM v_top_moving_items"
            " ORDER BY total_amount DESC LIMIT $1",
            limit
        )
    return [TopMoverSchema(**dict(r)) for r in rows]
