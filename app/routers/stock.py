from fastapi import APIRouter, Depends
import asyncpg

from app.core.database import get_conn
from app.repositories import stock_repo
from app.schemas.stock import StockItemSchema, StockGroupSchema, StockSummarySchema

router = APIRouter()


@router.get("/items", response_model=list[StockItemSchema])
async def list_items(
    group: str | None = None,
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        if group:
            return await stock_repo.get_items_by_group(c, group)
        return await stock_repo.get_all_items(c)


@router.get("/groups", response_model=list[StockGroupSchema])
async def list_groups(conn: asyncpg.Connection = Depends(get_conn)):
    async with conn as c:
        return await stock_repo.get_all_groups(c)


@router.get("/summary", response_model=StockSummarySchema)
async def summary(conn: asyncpg.Connection = Depends(get_conn)):
    async with conn as c:
        return await stock_repo.get_summary(c)


@router.get("/debug/tables", response_model=list[str])
async def debug_tables(conn: asyncpg.Connection = Depends(get_conn)):
    """List all tables in tallydb — use to find the correct group table."""
    async with conn as c:
        return await stock_repo.list_tallydb_tables(c)
