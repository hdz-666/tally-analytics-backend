from fastapi import APIRouter, Depends, Query
from datetime import date
import asyncpg

from app.core.database import get_conn

router = APIRouter()


@router.get("/by-group")
async def purchases_by_group(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    conditions = []
    args: list = []

    if from_date:
        args.append(from_date)
        conditions.append(f"month >= ${len(args)}")
    if to_date:
        args.append(to_date)
        conditions.append(f"month <= ${len(args)}")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    async with conn as c:
        rows = await c.fetch(
            f"SELECT * FROM v_purchase_by_group {where} ORDER BY stock_group, month", *args
        )
    return [dict(r) for r in rows]
