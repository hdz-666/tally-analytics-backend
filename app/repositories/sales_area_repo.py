import asyncpg
from datetime import date
from app.schemas.sales_area import (
    AreaSalesSchema,
    AreaClientSchema,
    ClientItemSchema,
    PincodeSalesSchema,
)


def _filter_conditions(
    from_date: date | None,
    to_date: date | None,
    item: str | None,
    stock_groups: list[str] | None,
    pincode: str | None,
    args: list,
) -> list[str]:
    conditions = []
    if from_date:
        args.append(from_date)
        conditions.append(f"month >= ${len(args)}")
    if to_date:
        args.append(to_date)
        conditions.append(f"month <= ${len(args)}")
    if item:
        args.append(item)
        conditions.append(f"item = ${len(args)}")
    if stock_groups:
        args.append(stock_groups)
        conditions.append(f"stock_group = ANY(${len(args)})")
    if pincode:
        args.append(pincode)
        conditions.append(f"pincode = ${len(args)}")
    return conditions


async def get_sales_by_area(
    conn: asyncpg.Connection,
    from_date: date | None = None,
    to_date: date | None = None,
    item: str | None = None,
    stock_groups: list[str] | None = None,
    pincode: str | None = None,
) -> list[AreaSalesSchema]:
    args: list = []
    conditions = _filter_conditions(
        from_date, to_date, item, stock_groups, pincode, args
    )
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = await conn.fetch(
        f"""
        WITH filtered AS (
            SELECT * FROM public.v_sales_by_area {where}
        ),
        -- A city's marker sits at its master pincode — the single pincode
        -- with the most sales in that city — rather than a computed average,
        -- which can drift to a point that isn't anywhere real.
        pincode_totals AS (
            SELECT area, pincode, lat, lon, SUM(sold_amount) AS amt
            FROM filtered
            WHERE pincode IS NOT NULL
            GROUP BY area, pincode, lat, lon
        ),
        master_point AS (
            SELECT DISTINCT ON (area) area, lat, lon
            FROM pincode_totals
            ORDER BY area, amt DESC
        ),
        area_totals AS (
            SELECT area,
                   MAX(state) AS state,
                   CASE
                       WHEN bool_or(resolution_level = 'pincode')
                           THEN 'pincode'
                       WHEN bool_or(resolution_level = 'town')
                           THEN 'town'
                       ELSE 'state'
                   END AS resolution_level,
                   SUM(sold_qty)              AS sold_qty,
                   SUM(sold_amount)           AS sold_amount,
                   COUNT(DISTINCT party_name) AS client_count,
                   -- fallback for areas with no pincode data at all
                   -- (town/state-only resolution)
                   SUM(lat * sold_amount) / NULLIF(SUM(sold_amount), 0)
                       AS fallback_lat,
                   SUM(lon * sold_amount) / NULLIF(SUM(sold_amount), 0)
                       AS fallback_lon
            FROM filtered
            GROUP BY area
        )
        SELECT
            t.area,
            COALESCE(m.lat, t.fallback_lat) AS lat,
            COALESCE(m.lon, t.fallback_lon) AS lon,
            t.state, t.resolution_level, t.sold_qty, t.sold_amount,
            t.client_count
        FROM area_totals t
        LEFT JOIN master_point m ON m.area = t.area
        ORDER BY t.sold_amount DESC
        """,
        *args,
    )
    return [AreaSalesSchema(**dict(r)) for r in rows]


async def get_clients_in_area(
    conn: asyncpg.Connection,
    area: str,
    from_date: date | None = None,
    to_date: date | None = None,
    item: str | None = None,
    stock_groups: list[str] | None = None,
    pincode: str | None = None,
) -> list[AreaClientSchema]:
    args: list = [area]
    conditions = ["area = $1"] + _filter_conditions(
        from_date, to_date, item, stock_groups, pincode, args
    )
    where = "WHERE " + " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT party_name,
               SUM(sold_qty)              AS sold_qty,
               SUM(sold_amount)           AS sold_amount,
               COUNT(DISTINCT item)       AS item_count
        FROM public.v_sales_by_area
        {where}
        GROUP BY party_name
        ORDER BY sold_amount DESC
        """,
        *args,
    )
    return [AreaClientSchema(**dict(r)) for r in rows]


async def get_pincodes_in_area(
    conn: asyncpg.Connection,
    area: str,
    from_date: date | None = None,
    to_date: date | None = None,
    item: str | None = None,
    stock_groups: list[str] | None = None,
) -> list[PincodeSalesSchema]:
    """Pincode-level breakdown within one city — the drill-down step between
    the city total and its clients, for locality-level targeting."""
    args: list = [area]
    conditions = ["area = $1", "pincode IS NOT NULL"] + _filter_conditions(
        from_date, to_date, item, stock_groups, None, args
    )
    where = "WHERE " + " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT pincode,
               MAX(area)                  AS area,
               MAX(state)                 AS state,
               MAX(lat)                   AS lat,
               MAX(lon)                   AS lon,
               SUM(sold_qty)              AS sold_qty,
               SUM(sold_amount)           AS sold_amount,
               COUNT(DISTINCT party_name) AS client_count
        FROM public.v_sales_by_area
        {where}
        GROUP BY pincode
        ORDER BY sold_amount DESC
        """,
        *args,
    )
    return [PincodeSalesSchema(**dict(r)) for r in rows]


async def get_items_for_client(
    conn: asyncpg.Connection,
    party_name: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[ClientItemSchema]:
    args: list = [party_name]
    conditions = ["party_name = $1"] + _filter_conditions(
        from_date, to_date, None, None, None, args
    )
    where = "WHERE " + " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT item, stock_group,
               SUM(sold_qty)      AS sold_qty,
               SUM(sold_amount)   AS sold_amount
        FROM public.v_sales_by_area
        {where}
        GROUP BY item, stock_group
        ORDER BY sold_amount DESC
        """,
        *args,
    )
    return [ClientItemSchema(**dict(r)) for r in rows]


async def get_pincodes(
    conn: asyncpg.Connection,
    from_date: date | None = None,
    to_date: date | None = None,
    item: str | None = None,
    stock_groups: list[str] | None = None,
) -> list[PincodeSalesSchema]:
    """Distinct pincodes seen in the data — a finer-grained, searchable
    complement to the city-level `area` rollup (one city can span several
    pincodes, and the sales team may want to zoom into just one of them).
    """
    args: list = []
    conditions = ["pincode IS NOT NULL"] + _filter_conditions(
        from_date, to_date, item, stock_groups, None, args
    )
    where = "WHERE " + " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT pincode,
               MAX(area)                  AS area,
               MAX(state)                 AS state,
               MAX(lat)                   AS lat,
               MAX(lon)                   AS lon,
               SUM(sold_qty)              AS sold_qty,
               SUM(sold_amount)           AS sold_amount,
               COUNT(DISTINCT party_name) AS client_count
        FROM public.v_sales_by_area
        {where}
        GROUP BY pincode
        ORDER BY sold_amount DESC
        """,
        *args,
    )
    return [PincodeSalesSchema(**dict(r)) for r in rows]
