import json
import urllib.error
import urllib.request

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

_bearer = HTTPBearer()


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
