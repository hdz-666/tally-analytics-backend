import os

# Must be set before any app imports so pydantic-settings doesn't fail
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test_db")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.auth import get_current_user
from app.core.database import get_conn

MOCK_USER = {"id": "test-user-id", "email": "test@example.com"}


class MockTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class MockConnection:
    """Mock asyncpg connection: supports async context manager + DB query methods."""

    def __init__(self):
        self.fetch = AsyncMock(return_value=[])
        self.fetchrow = AsyncMock(return_value=None)
        self.execute = AsyncMock(return_value=None)
        self.copy_records_to_table = AsyncMock(return_value=None)

    def transaction(self):
        return MockTransaction()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.fixture
def mock_conn():
    return MockConnection()


@pytest.fixture
def override_app(mock_conn):
    """FastAPI app with auth and DB dependencies replaced by test doubles."""
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_conn] = lambda: mock_conn
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_app):
    async with AsyncClient(
        transport=ASGITransport(app=override_app),
        base_url="http://testserver",
    ) as ac:
        yield ac
