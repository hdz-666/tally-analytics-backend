from fastapi import APIRouter, Depends
import asyncpg

from app.core.database import get_conn
from app.repositories import ledger_repo
from app.schemas.ledger import LedgerHealthSchema, PnlMonthlySchema

router = APIRouter()


@router.get("/health", response_model=list[LedgerHealthSchema])
async def ledger_health(conn: asyncpg.Connection = Depends(get_conn)):
    async with conn as c:
        return await ledger_repo.get_ledger_health(c)


@router.get("/pnl", response_model=list[PnlMonthlySchema])
async def pnl_monthly(conn: asyncpg.Connection = Depends(get_conn)):
    async with conn as c:
        return await ledger_repo.get_pnl_monthly(c)


@router.post("/refresh")
async def refresh_ledger_views(conn: asyncpg.Connection = Depends(get_conn)):
    async with conn as c:
        await ledger_repo.refresh_views(c)
    return {"message": "Ledger views refreshed successfully"}
