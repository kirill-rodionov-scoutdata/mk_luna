import json
import pathlib
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from dependency_injector import providers
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.app_layer.services.outbox import OutboxService
from app.app_layer.services.payment import PaymentService
from app.config import settings
from app.domain.models.payment import PaymentEntity
from app.main import app
from tests.environment.publisher import FakePublisher
from tests.environment.unit_of_work import TestUow
from tests.satellites import (
    make_outbox_service,
    make_payment_entity,
    make_payment_service,
)


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    eng = create_async_engine(settings.database.url, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
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
async def client(
    db_session: AsyncSession, fake_publisher: FakePublisher
) -> AsyncGenerator[AsyncClient, None]:
    container = app.state.container
    test_uow = TestUow(db_session)

    container.wire(packages=["app.api"])

    with container.unit_of_work.override(providers.Object(test_uow)):
        with container.event_publisher.override(providers.Object(fake_publisher)):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"X-API-Key": settings.api.api_key},
            ) as ac:
                yield ac


@pytest.fixture(scope="session")
def payment_records() -> list[dict[str, Any]]:
    path = pathlib.Path(__file__).parent / "data" / "payments.json"
    return json.loads(path.read_text())


@pytest.fixture
def payment_entity(payment_records: list[dict[str, Any]]) -> PaymentEntity:
    return make_payment_entity(payment_records[0])


@pytest.fixture
def payment_service(db_session: AsyncSession) -> PaymentService:
    return make_payment_service(TestUow(db_session))


@pytest.fixture
def outbox_service(db_session: AsyncSession) -> OutboxService:
    return make_outbox_service(TestUow(db_session))
