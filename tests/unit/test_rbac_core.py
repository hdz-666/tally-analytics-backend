import io
import json
import urllib.error
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core import supabase_admin
from app.core.auth import (
    ADMIN,
    COMPANY_EXEC,
    EXECUTIVE,
    Principal,
    get_principal,
    load_principal,
    require_roles,
)
from tests.conftest import MockConnection

USER = {"id": "u1", "email": "a@b.c"}


# ── get_principal ────────────────────────────────────────────────────────────

async def test_principal_without_role_is_403():
    conn = MockConnection()
    conn.fetchval.return_value = None
    with pytest.raises(HTTPException) as exc:
        await load_principal(conn, USER)
    assert exc.value.status_code == 403


async def test_admin_principal_is_unscoped():
    conn = MockConnection()
    conn.fetchval.return_value = ADMIN
    p = await load_principal(conn, USER)
    assert p.role == ADMIN
    assert p.group_scope is None
    conn.fetch.assert_not_called()


async def test_company_exec_principal_loads_group_tree():
    conn = MockConnection()
    conn.fetchval.return_value = COMPANY_EXEC
    conn.fetch.side_effect = [
        [{"stock_group": "Gloirio"}],
        [{"name": "G-Kids"}, {"name": "Gloirio"}],
    ]
    p = await load_principal(conn, USER)
    assert p.categories == ("Gloirio",)
    assert p.group_scope == ["G-Kids", "Gloirio"]
    tree_sql = conn.fetch.call_args_list[1].args[0]
    assert "WITH RECURSIVE" in tree_sql


async def test_company_exec_with_no_categories_gets_empty_scope():
    conn = MockConnection()
    conn.fetchval.return_value = COMPANY_EXEC
    conn.fetch.side_effect = [[], []]
    p = await load_principal(conn, USER)
    assert p.group_scope == []


# ── require_roles ────────────────────────────────────────────────────────────

async def test_require_roles_allows_and_denies():
    check = require_roles(ADMIN, EXECUTIVE)
    exec_ = Principal(id="u1", email=None, role=EXECUTIVE)
    assert await check(exec_) is exec_
    with pytest.raises(HTTPException) as exc:
        await check(Principal(id="u1", email=None, role=COMPANY_EXEC))
    assert exc.value.status_code == 403


# ── supabase_admin ───────────────────────────────────────────────────────────

def ok_response(body: bytes):
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__.return_value = resp
    return resp


def test_create_user_posts_confirmed_user():
    resp = ok_response(json.dumps({"id": "new"}).encode())
    with patch(
        "app.core.supabase_admin.urllib.request.urlopen", return_value=resp
    ) as urlopen:
        assert supabase_admin.create_user("a@b.c", "pw123456") == {"id": "new"}
    req = urlopen.call_args.args[0]
    assert req.full_url == "https://test.supabase.co/auth/v1/admin/users"
    assert req.get_method() == "POST"
    assert json.loads(req.data) == {
        "email": "a@b.c", "password": "pw123456", "email_confirm": True,
    }
    assert req.get_header("Apikey") == "test-secret-key"


def test_delete_user_handles_empty_body():
    with patch(
        "app.core.supabase_admin.urllib.request.urlopen",
        return_value=ok_response(b""),
    ) as urlopen:
        supabase_admin.delete_user("u9")
    req = urlopen.call_args.args[0]
    assert req.get_method() == "DELETE"
    assert req.full_url.endswith("/auth/v1/admin/users/u9")


@pytest.mark.parametrize("code,body,expected_code,expected_detail", [
    (422, b'{"msg": "User already registered"}', 422,
     "User already registered"),
    (500, b"not json", 502, "Supabase Auth request failed"),
])
def test_admin_errors_map_to_http_exception(
    code, body, expected_code, expected_detail
):
    err = urllib.error.HTTPError("url", code, "x", {}, io.BytesIO(body))
    with patch(
        "app.core.supabase_admin.urllib.request.urlopen", side_effect=err
    ):
        with pytest.raises(HTTPException) as exc:
            supabase_admin.create_user("a@b.c", "pw123456")
    assert exc.value.status_code == expected_code
    assert exc.value.detail == expected_detail
