"""
Shared test fixtures.

TODO (implementation phase):
  - async_engine: spin up a test PostgreSQL DB (or use SQLite+aiosqlite for unit tests)
  - async_session: scoped session per test, rolls back after each test
  - client: AsyncClient wrapping the FastAPI app with overridden container
  - fake_broker: in-memory FastStream broker for consumer tests
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """HTTP test client. Uses the real app with real container wiring."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": settings.api_key},
    ) as c:
        yield c
