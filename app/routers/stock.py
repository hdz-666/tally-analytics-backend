from fastapi import APIRouter, Depends
import asyncpg

from app.core.auth import (
    ADMIN,
    COMPANY_EXEC,
    EXECUTIVE,
    Principal,
    get_principal,
    require_roles,
)
from app.core.database import get_conn
from app.repositories import stock_repo
from app.schemas.stock import StockItemSchema, StockGroupSchema, StockSummarySchema

router = APIRouter()


@router.get("/items", response_model=list[StockItemSchema])
async def list_items(
    group: str | None = None,
    conn: asyncpg.Connection = Depends(get_conn),
    principal: Principal = Depends(get_principal),
):
    async with conn as c:
        if group:
            items = await stock_repo.get_items_by_group(c, group)
        else:
            items = await stock_repo.get_all_items(c)
    if principal.role != COMPANY_EXEC:
        return items
    # Company execs only get their own categories, and never value or rate.
    allowed = set(principal.allowed_groups or ())
    return [
        StockItemSchema(
            name=i.name,
            stock_group=i.stock_group,
            closing_balance=i.closing_balance,
        )
        for i in items
        if i.stock_group in allowed
    ]


@router.get("/groups", response_model=list[StockGroupSchema])
async def list_groups(
    conn: asyncpg.Connection = Depends(get_conn),
    principal: Principal = Depends(get_principal),
):
    async with conn as c:
        groups = await stock_repo.get_all_groups(c)
    if principal.role != COMPANY_EXEC:
        return groups
    # Detach the exec's top-level categories from parents they can't see so
    # they render as tree roots in the group pickers.
    allowed = set(principal.allowed_groups or ())
    return [
        StockGroupSchema(
            name=g.name,
            parent=g.parent if g.parent in allowed else None,
        )
        for g in groups
        if g.name in allowed
    ]


@router.get(
    "/summary",
    response_model=StockSummarySchema,
    dependencies=[Depends(require_roles(ADMIN, EXECUTIVE))],
)
async def summary(conn: asyncpg.Connection = Depends(get_conn)):
    async with conn as c:
        return await stock_repo.get_summary(c)


@router.get(
    "/debug/tables",
    response_model=list[str],
    dependencies=[Depends(require_roles(ADMIN))],
)
async def debug_tables(conn: asyncpg.Connection = Depends(get_conn)):
    """List all tables in tallydb — use to find the correct group table."""
    async with conn as c:
        return await stock_repo.list_tallydb_tables(c)
