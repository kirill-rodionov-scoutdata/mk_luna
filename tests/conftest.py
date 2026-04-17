import pytest
import pytest_asyncio
from dependency_injector import providers
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.main import app
from tests.environment.publisher import FakePublisher
from tests.environment.unit_of_work import TestUow


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def engine():
    eng = create_async_engine(settings.database_url, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """
    Yields an AsyncSession bound to an open (not yet committed) connection.
    All writes made during a test are rolled back when this fixture tears down.
    """
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest.fixture
def fake_publisher() -> FakePublisher:
    return FakePublisher()

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, fake_publisher: FakePublisher) -> AsyncClient:
    container = app.state.container
    test_uow = TestUow(db_session)

    # Ensure DI wiring is in place before any request is handled.
    container.wire(packages=["app.api"])

    with container.unit_of_work.override(providers.Object(test_uow)):
        with container.event_publisher.override(providers.Object(fake_publisher)):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"X-API-Key": settings.api_key},
            ) as ac:
                yield ac
