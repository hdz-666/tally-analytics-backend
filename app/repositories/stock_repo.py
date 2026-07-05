import asyncpg
from app.schemas.stock import StockItemSchema, StockGroupSchema, StockSummarySchema


async def get_all_items(conn: asyncpg.Connection) -> list[StockItemSchema]:
    rows = await conn.fetch(
        "SELECT * FROM v_current_stock ORDER BY stock_group, name"
    )
    return [StockItemSchema(**dict(r)) for r in rows]


async def _group_table(conn: asyncpg.Connection) -> str | None:
    """Return the fully-qualified group table name, or None if absent."""
    row = await conn.fetchrow("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'tallydb'
          AND table_name ILIKE '%stock%group%'
        ORDER BY table_name
        LIMIT 1
    """)
    return f"tallydb.{row['table_name']}" if row else None


async def get_items_by_group(conn: asyncpg.Connection, group: str) -> list[StockItemSchema]:
    tbl = await _group_table(conn)
    if tbl:
        rows = await conn.fetch(f"""
            WITH RECURSIVE group_tree AS (
                SELECT name FROM {tbl} WHERE name = $1
                UNION ALL
                SELECT g.name
                FROM {tbl} g
                JOIN group_tree gt ON NULLIF(g.parent, '') = gt.name
            )
            SELECT cs.*
            FROM v_current_stock cs
            WHERE cs.stock_group = ANY(SELECT name FROM group_tree)
            ORDER BY cs.stock_group, cs.name
        """, group)
    else:
        # No group hierarchy table — simple exact match
        rows = await conn.fetch(
            "SELECT * FROM v_current_stock WHERE stock_group = $1 ORDER BY name", group
        )
    return [StockItemSchema(**dict(r)) for r in rows]


async def get_all_groups(conn: asyncpg.Connection) -> list[StockGroupSchema]:
    tbl = await _group_table(conn)
    if tbl:
        rows = await conn.fetch(f"""
            SELECT name, NULLIF(parent, '') AS parent
            FROM {tbl}
            ORDER BY parent NULLS FIRST, name
        """)
        return [StockGroupSchema(name=r["name"], parent=r["parent"]) for r in rows]
    # Fallback: derive flat group list from items (no nesting info available)
    rows = await conn.fetch("""
        SELECT DISTINCT stock_group AS name
        FROM v_current_stock
        WHERE stock_group IS NOT NULL
        ORDER BY 1
    """)
    return [StockGroupSchema(name=r["name"], parent=None) for r in rows]


async def list_tallydb_tables(conn: asyncpg.Connection) -> list[str]:
    """Diagnostic: return all table names in the tallydb schema."""
    rows = await conn.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'tallydb'
        ORDER BY table_name
    """)
    return [r["table_name"] for r in rows]


async def get_summary(conn: asyncpg.Connection) -> StockSummarySchema:
    row = await conn.fetchrow("""
        SELECT
            COUNT(*)                                                AS total_items,
            COALESCE(SUM(closing_value), 0)                        AS total_value,
            COUNT(*) FILTER (WHERE closing_balance <= 0)           AS out_of_stock_count,
            COUNT(*) FILTER (WHERE needs_reorder = true)           AS low_stock_count
        FROM v_current_stock cs
        LEFT JOIN v_reorder_alerts ra ON ra.item = cs.name
    """)
    return StockSummarySchema(**dict(row))
