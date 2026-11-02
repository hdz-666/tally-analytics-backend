import json
import urllib.error
import urllib.request
from dataclasses import dataclass

import asyncpg
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import get_conn
from app.repositories import user_repo

_bearer = HTTPBearer()

ADMIN = "admin"
EXECUTIVE = "executive"
COMPANY_EXEC = "company_exec"
ROLES = (ADMIN, EXECUTIVE, COMPANY_EXEC)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> dict:
    token = credentials.credentials
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": settings.supabase_secret_key,
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@dataclass(frozen=True)
class Principal:
    id: str
    email: str | None
    role: str
    # Top-level stock groups assigned to a company exec (as stored).
    categories: tuple[str, ...] = ()
    # Those groups plus every descendant — what queries are filtered by.
    # None means unrestricted; an empty tuple means "sees nothing".
    allowed_groups: tuple[str, ...] | None = None

    @property
    def group_scope(self) -> list[str] | None:
        if self.allowed_groups is None:
            return None
        return list(self.allowed_groups)


async def get_principal(user: dict = Depends(get_current_user)) -> Principal:
    # Takes its own pool checkout rather than Depends(get_conn): FastAPI
    # caches a dependency's result per request even with use_cache=False, so
    # the route's get_conn would be handed this already-used checkout and
    # asyncpg raises "a connection is already acquired".
    return await load_principal(await get_conn(), user)


async def load_principal(
    conn: asyncpg.Connection, user: dict
) -> Principal:
    async with conn as c:
        role = await user_repo.get_role(c, user["id"])
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No role assigned to this account",
            )
        categories: list[str] = []
        allowed: list[str] | None = None
        if role == COMPANY_EXEC:
            categories = await user_repo.get_categories(c, user["id"])
            allowed = await user_repo.get_allowed_groups(c, user["id"])

    return Principal(
        id=user["id"],
        email=user.get("email"),
        role=role,
        categories=tuple(categories),
        allowed_groups=None if allowed is None else tuple(allowed),
    )


def require_roles(*roles: str):
    async def check(
        principal: Principal = Depends(get_principal),
    ) -> Principal:
        if principal.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource",
            )
        return principal

    return check
