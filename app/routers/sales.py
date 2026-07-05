from fastapi import APIRouter, Depends, Query
from datetime import date
import asyncpg

from app.core.database import get_conn
from app.repositories import sales_repo
from app.schemas.sales import MonthlySalesSchema, GroupSalesSchema, TopMoverSchema

router = APIRouter()


@router.get("/monthly", response_model=list[MonthlySalesSchema])
async def monthly_sales(
    item: str | None = None,
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await sales_repo.get_monthly_sales(c, item, from_date, to_date)


@router.get("/by-group", response_model=list[GroupSalesSchema])
async def sales_by_group(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await sales_repo.get_sales_by_group(c, from_date, to_date)


@router.get("/top-movers", response_model=list[TopMoverSchema])
async def top_movers(
    limit: int = Query(20, ge=1, le=100),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await sales_repo.get_top_movers(c, limit)
