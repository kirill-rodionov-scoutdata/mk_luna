import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.domain.models.outbox import OutboxEventType
from app.infra.db.models import OutboxORM
from app.infra.rabbitmq.exceptions import OutboxPersistenceError
from app.infra.rabbitmq.outbox_relay import OutboxRelay
from app.infra.unit_of_work.alchemy import AlchemyUnitOfWork
from tests.environment.publisher import FakePublisher


class FailingPublisher:
    def __init__(self) -> None:
        self.published_messages: list[dict[str, Any]] = []

    async def publish(self, _routing_key: str, _payload: dict[str, Any]) -> None:
        raise Exception("broker unavailable")


@pytest.mark.asyncio
async def test_outbox_relay_publishes_and_marks_events(
    engine: AsyncEngine,
    fake_publisher: FakePublisher,
    payment_records: list[dict[str, Any]],
) -> None:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    relay = OutboxRelay(session_factory=session_factory, publisher=fake_publisher)
    payload: dict[str, Any] = {"payment_id": payment_records[0]["idempotency_key"]}

    async with AlchemyUnitOfWork(session_factory) as uow:
        await uow.outbox.add(event_type=OutboxEventType.PAYMENTS_NEW, payload=payload)
        await uow.commit()

    await relay.process_batch()

    assert len(fake_publisher.published_messages) == 1
    published_msg = fake_publisher.published_messages[0]
    assert published_msg["routing_key"] == OutboxEventType.PAYMENTS_NEW
    assert published_msg["payload"] == payload

    async with session_factory() as session:
        result = await session.execute(
            OutboxORM.__table__.select().where(
                OutboxORM.payload["payment_id"].astext == payload["payment_id"]
            )
        )
        row = result.fetchone()
        assert row is not None
        assert row.published is True


@pytest.mark.asyncio
async def test_outbox_relay_skips_event_when_publish_fails(
    engine: AsyncEngine,
    payment_records: list[dict[str, Any]],
) -> None:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    failing_publisher = FailingPublisher()
    relay = OutboxRelay(session_factory=session_factory, publisher=failing_publisher)
    payload: dict[str, Any] = {"payment_id": payment_records[1]["idempotency_key"]}

    async with AlchemyUnitOfWork(session_factory) as uow:
        await uow.outbox.add(event_type=OutboxEventType.PAYMENTS_NEW, payload=payload)
        await uow.commit()

    await relay.process_batch()

    assert len(failing_publisher.published_messages) == 0

    async with session_factory() as session:
        result = await session.execute(
            OutboxORM.__table__.select().where(
                OutboxORM.payload["payment_id"].astext == payload["payment_id"]
            )
        )
        rows = result.fetchall()
        assert len(rows) > 0
        assert all(row.published is False for row in rows)


@pytest.mark.asyncio
async def test_outbox_relay_does_not_mark_published_when_db_fails(
    engine: AsyncEngine,
    fake_publisher: FakePublisher,
    payment_records: list[dict[str, Any]],
) -> None:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    relay = OutboxRelay(session_factory=session_factory, publisher=fake_publisher)
    payment_id = payment_records[2]["idempotency_key"]
    payload: dict[str, Any] = {"payment_id": payment_id}

    async with AlchemyUnitOfWork(session_factory) as uow:
        await uow.outbox.add(event_type=OutboxEventType.PAYMENTS_NEW, payload=payload)
        await uow.commit()

    with patch.object(
        relay,
        "mark_published",
        AsyncMock(side_effect=OutboxPersistenceError(uuid.uuid4(), Exception("DB write failed"))),
    ):
        await relay.process_batch()

    assert any(
        m["payload"]["payment_id"] == payment_id for m in fake_publisher.published_messages
    )

    async with session_factory() as session:
        result = await session.execute(
            OutboxORM.__table__.select().where(
                OutboxORM.payload["payment_id"].astext == payment_id
            )
        )
        rows = result.fetchall()
        assert len(rows) > 0
        assert all(row.published is False for row in rows)
