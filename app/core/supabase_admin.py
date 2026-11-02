"""Supabase Auth admin API — creating and deleting login accounts needs the
secret key, so it lives server-side and is only reachable by admins."""
import json
import urllib.error
import urllib.request

from fastapi import HTTPException, status

from app.core.config import settings


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin{path}"
    req = urllib.request.Request(
        url,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {settings.supabase_secret_key}",
            "apikey": settings.supabase_secret_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())
        except ValueError:
            err = {}
        detail = (
            err.get("msg")
            or err.get("message")
            or err.get("error_description")
            or "Supabase Auth request failed"
        )
        code = e.code if 400 <= e.code < 500 else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(status_code=code, detail=detail)


def create_user(email: str, password: str) -> dict:
    # email_confirm: the admin vouches for the address, so the user can sign
    # in straight away without a confirmation email.
    return _request(
        "POST",
        "/users",
        {"email": email, "password": password, "email_confirm": True},
    )


def delete_user(user_id: str) -> None:
    _request("DELETE", f"/users/{user_id}")
