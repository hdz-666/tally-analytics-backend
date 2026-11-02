from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.auth import COMPANY_EXEC, EXECUTIVE, Principal

OTHER_ID = "11111111-1111-1111-1111-111111111111"


# ── GET /api/me ──────────────────────────────────────────────────────────────

async def test_me_returns_role_and_categories(client, as_principal):
    as_principal(Principal(
        id="u1", email="exec@x.com", role=COMPANY_EXEC,
        categories=("Gloirio",), allowed_groups=("Gloirio", "G-Kids"),
    ))
    data = (await client.get("/api/me")).json()
    assert data == {
        "id": "u1", "email": "exec@x.com",
        "role": "company_exec", "categories": ["Gloirio"],
    }


# ── GET /api/users ───────────────────────────────────────────────────────────

async def test_list_users(client, mock_conn):
    mock_conn.fetch.return_value = [
        {"id": OTHER_ID, "email": "a@x.com",
         "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
         "last_sign_in_at": None, "role": None, "categories": []},
    ]
    data = (await client.get("/api/users")).json()
    assert data[0]["email"] == "a@x.com"
    assert data[0]["role"] is None


# ── POST /api/users ──────────────────────────────────────────────────────────

async def test_create_user_creates_login_then_assigns_access(
    client, mock_conn, mocker
):
    create = mocker.patch(
        "app.routers.users.supabase_admin.create_user",
        return_value={"id": OTHER_ID, "email": "new@x.com"},
    )
    response = await client.post("/api/users", json={
        "email": "new@x.com", "password": "secret123",
        "role": "company_exec", "categories": ["Gloirio"],
    })
    assert response.status_code == 201
    assert response.json()["role"] == "company_exec"
    create.assert_called_once_with("new@x.com", "secret123")
    calls = [c.args for c in mock_conn.execute.call_args_list]
    assert calls[0][1:] == (OTHER_ID, "company_exec")
    assert calls[-1][1:] == (OTHER_ID, ["Gloirio"])


async def test_create_company_exec_requires_category(client, mocker):
    create = mocker.patch("app.routers.users.supabase_admin.create_user")
    response = await client.post("/api/users", json={
        "email": "new@x.com", "password": "secret123",
        "role": "company_exec", "categories": [],
    })
    assert response.status_code == 422
    create.assert_not_called()


async def test_create_user_rejects_short_password(client):
    response = await client.post("/api/users", json={
        "email": "new@x.com", "password": "short", "role": "executive",
    })
    assert response.status_code == 422


async def test_create_user_surfaces_supabase_error(client, mocker):
    mocker.patch(
        "app.routers.users.supabase_admin.create_user",
        side_effect=HTTPException(422, "User already registered"),
    )
    response = await client.post("/api/users", json={
        "email": "dup@x.com", "password": "secret123", "role": "executive",
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "User already registered"


# ── PUT /api/users/{id} ──────────────────────────────────────────────────────

async def test_update_access_drops_categories_for_non_company_exec(
    client, mock_conn
):
    mock_conn.fetchval.return_value = True
    response = await client.put(f"/api/users/{OTHER_ID}", json={
        "role": "executive", "categories": ["Gloirio"],
    })
    assert response.json() == {"role": "executive", "categories": []}
    # role upsert + category delete, no category insert
    assert mock_conn.execute.call_count == 2


async def test_update_access_unknown_user_is_404(client, mock_conn):
    mock_conn.fetchval.return_value = False
    response = await client.put(
        f"/api/users/{OTHER_ID}", json={"role": "executive"}
    )
    assert response.status_code == 404


async def test_admin_cannot_demote_self(client, as_principal):
    me = "22222222-2222-2222-2222-222222222222"
    as_principal(Principal(id=me, email="a@x.com", role="admin"))
    response = await client.put(
        f"/api/users/{me}", json={"role": EXECUTIVE}
    )
    assert response.status_code == 400


async def test_update_access_rejects_bad_id(client):
    response = await client.put(
        "/api/users/not-a-uuid", json={"role": "executive"}
    )
    assert response.status_code == 422


# ── DELETE /api/users/{id} ───────────────────────────────────────────────────

async def test_delete_user(client, mocker):
    delete = mocker.patch("app.routers.users.supabase_admin.delete_user")
    response = await client.delete(f"/api/users/{OTHER_ID}")
    assert response.status_code == 204
    delete.assert_called_once_with(OTHER_ID)


async def test_admin_cannot_delete_self(client, as_principal, mocker):
    me = "22222222-2222-2222-2222-222222222222"
    as_principal(Principal(id=me, email="a@x.com", role="admin"))
    delete = mocker.patch("app.routers.users.supabase_admin.delete_user")
    response = await client.delete(f"/api/users/{me}")
    assert response.status_code == 400
    delete.assert_not_called()
