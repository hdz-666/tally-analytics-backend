import asyncpg

from app.schemas.users import AppUserSchema


async def get_role(conn: asyncpg.Connection, user_id: str) -> str | None:
    return await conn.fetchval(
        "SELECT role FROM public.user_roles WHERE user_id = $1::uuid",
        user_id,
    )


async def get_categories(conn: asyncpg.Connection, user_id: str) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT stock_group FROM public.user_categories
        WHERE user_id = $1::uuid
        ORDER BY stock_group
        """,
        user_id,
    )
    return [r["stock_group"] for r in rows]


async def get_allowed_groups(
    conn: asyncpg.Connection, user_id: str
) -> list[str]:
    """The user's assigned stock groups plus every group nested under them —
    items are tagged with their leaf group, so filtering needs the full tree.
    UNION (not UNION ALL) stops a cyclic parent chain from looping forever.
    """
    rows = await conn.fetch(
        """
        WITH RECURSIVE tree AS (
            SELECT stock_group AS name
            FROM public.user_categories
            WHERE user_id = $1::uuid
            UNION
            SELECT g.name
            FROM tallydb.mst_stock_group g
            JOIN tree t ON NULLIF(g.parent, '') = t.name
        )
        SELECT name FROM tree ORDER BY name
        """,
        user_id,
    )
    return [r["name"] for r in rows]


async def list_users(conn: asyncpg.Connection) -> list[AppUserSchema]:
    rows = await conn.fetch(
        """
        SELECT u.id::text AS id,
               u.email,
               u.created_at,
               u.last_sign_in_at,
               r.role,
               COALESCE(
                   array_agg(c.stock_group ORDER BY c.stock_group)
                       FILTER (WHERE c.stock_group IS NOT NULL),
                   '{}'
               ) AS categories
        FROM auth.users u
        LEFT JOIN public.user_roles r      ON r.user_id = u.id
        LEFT JOIN public.user_categories c ON c.user_id = u.id
        GROUP BY u.id, u.email, u.created_at, u.last_sign_in_at, r.role
        ORDER BY u.email
        """
    )
    return [AppUserSchema(**dict(r)) for r in rows]


async def set_access(
    conn: asyncpg.Connection,
    user_id: str,
    role: str,
    categories: list[str],
) -> None:
    """Replace a user's role and category assignments in one transaction."""
    async with conn.transaction():
        await conn.execute(
            """
            INSERT INTO public.user_roles (user_id, role)
            VALUES ($1::uuid, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET role = EXCLUDED.role, updated_at = now()
            """,
            user_id,
            role,
        )
        await conn.execute(
            "DELETE FROM public.user_categories WHERE user_id = $1::uuid",
            user_id,
        )
        if categories:
            await conn.execute(
                """
                INSERT INTO public.user_categories (user_id, stock_group)
                SELECT $1::uuid, unnest($2::text[])
                ON CONFLICT DO NOTHING
                """,
                user_id,
                categories,
            )


async def user_exists(conn: asyncpg.Connection, user_id: str) -> bool:
    return bool(
        await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM auth.users WHERE id = $1::uuid)",
            user_id,
        )
    )
