import asyncpg
from app.core.config import settings

_pool: asyncpg.Pool | None = None


async def create_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
        command_timeout=60,
        statement_cache_size=0,
        server_settings={"search_path": "public,tallydb"},
    )


async def close_pool() -> None:
    if _pool:
        await _pool.close()


async def get_conn() -> asyncpg.Connection:
    return _pool.acquire()
