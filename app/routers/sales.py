from fastapi import APIRouter, Depends, Query
from datetime import date
import asyncpg

from app.core.database import get_conn
from app.repositories import sales_repo, sales_area_repo
from app.schemas.sales import (
    MonthlySalesSchema,
    GroupSalesSchema,
    TopMoverSchema,
)
from app.schemas.sales_area import (
    AreaSalesSchema,
    AreaClientSchema,
    ClientItemSchema,
    PincodeSalesSchema,
)

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
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    stock_group: str | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await sales_repo.get_top_movers(
            c, limit, from_date, to_date, stock_group
        )


@router.get("/by-area", response_model=list[AreaSalesSchema])
async def sales_by_area(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    item: str | None = Query(None),
    stock_group: list[str] | None = Query(None),
    pincode: str | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await sales_area_repo.get_sales_by_area(
            c, from_date, to_date, item, stock_group, pincode
        )


@router.get("/by-area/{area}/clients", response_model=list[AreaClientSchema])
async def area_clients(
    area: str,
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    item: str | None = Query(None),
    stock_group: list[str] | None = Query(None),
    pincode: str | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await sales_area_repo.get_clients_in_area(
            c, area, from_date, to_date, item, stock_group, pincode
        )


@router.get("/by-area/{area}/pincodes", response_model=list[PincodeSalesSchema])
async def area_pincodes(
    area: str,
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    item: str | None = Query(None),
    stock_group: list[str] | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await sales_area_repo.get_pincodes_in_area(
            c, area, from_date, to_date, item, stock_group
        )


@router.get("/clients/{party_name}/items", response_model=list[ClientItemSchema])
async def client_items(
    party_name: str,
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await sales_area_repo.get_items_for_client(
            c, party_name, from_date, to_date
        )


@router.get("/pincodes", response_model=list[PincodeSalesSchema])
async def pincodes(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    item: str | None = Query(None),
    stock_group: list[str] | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    async with conn as c:
        return await sales_area_repo.get_pincodes(
            c, from_date, to_date, item, stock_group
        )
