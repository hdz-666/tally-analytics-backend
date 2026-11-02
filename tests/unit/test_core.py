import io
import json
import urllib.error
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import database
from app.core.auth import get_current_user
from app.core.config import Settings
from app.main import app


def creds(token: str = "tok") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# ── auth ─────────────────────────────────────────────────────────────────────

def test_get_current_user_returns_supabase_user():
    resp = MagicMock()
    resp.read.return_value = json.dumps({"id": "u1", "email": "a@b.c"}).encode()
    resp.__enter__.return_value = resp

    with patch("app.core.auth.urllib.request.urlopen", return_value=resp) as urlopen:
        user = get_current_user(creds("abc"))

    assert user == {"id": "u1", "email": "a@b.c"}
    req = urlopen.call_args.args[0]
    assert req.full_url == "https://test.supabase.co/auth/v1/user"
    assert req.get_header("Authorization") == "Bearer abc"
    assert req.get_header("Apikey") == "test-secret-key"


def test_get_current_user_invalid_token_is_401():
    err = urllib.error.HTTPError("url", 401, "Unauthorized", {}, io.BytesIO(b""))
    with patch("app.core.auth.urllib.request.urlopen", side_effect=err):
        with pytest.raises(HTTPException) as exc:
            get_current_user(creds())
    assert exc.value.status_code == 401
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}


# ── config ───────────────────────────────────────────────────────────────────

def test_origins_list_splits_and_strips():
    s = Settings(
        database_url="x", supabase_url="x", supabase_secret_key="x",
        allowed_origins="http://a.com, http://b.com ,http://c.com",
    )
    assert s.origins_list == ["http://a.com", "http://b.com", "http://c.com"]


# ── database ─────────────────────────────────────────────────────────────────

async def test_pool_lifecycle():
    pool = MagicMock()
    pool.close = AsyncMock()
    with patch("app.core.database.asyncpg.create_pool", AsyncMock(return_value=pool)) as create:
        await database.create_pool()
    try:
        assert create.call_args.kwargs["statement_cache_size"] == 0
        assert await database.get_conn() is pool.acquire.return_value
        await database.close_pool()
        pool.close.assert_awaited_once()
    finally:
        database._pool = None


async def test_close_pool_without_pool_is_noop():
    database._pool = None
    await database.close_pool()


# ── app lifespan ─────────────────────────────────────────────────────────────

async def test_lifespan_opens_and_closes_pool():
    with (
        patch("app.main.create_pool", AsyncMock()) as create,
        patch("app.main.close_pool", AsyncMock()) as close,
    ):
        async with app.router.lifespan_context(app):
            create.assert_awaited_once()
            close.assert_not_awaited()
        close.assert_awaited_once()
