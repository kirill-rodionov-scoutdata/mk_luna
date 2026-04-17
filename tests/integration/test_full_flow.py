from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.domain.models.outbox import OutboxEventType
from app.domain.models.payment import PaymentStatus
from app.infra.db.models import OutboxORM, PaymentORM
from app.infra.rabbitmq.outbox_relay import OutboxRelay
from tests.environment.publisher import FakePublisher


@pytest.mark.asyncio
async def test_full_payment_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_publisher: FakePublisher,
    payment_records: list[dict[str, Any]],
) -> None:
    def mock_session_factory() -> AsyncSession:
        return db_session

    record = payment_records[0].copy()
    headers = {"Idempotency-Key": str(record.pop("idempotency_key"))}

    response = await client.post("/api/v1/payments", json=record, headers=headers)

    assert response.status_code == 202
    data = response.json()
    assert "payment_id" in data
    payment_id = data["payment_id"]

    payment = await db_session.get(PaymentORM, payment_id)
    assert payment is not None
    assert payment.status == PaymentStatus.PENDING.value

    result = await db_session.execute(
        OutboxORM.__table__.select().where(
            OutboxORM.payload["payment_id"].astext == payment_id
        )
    )
    outbox_row = result.fetchone()
    assert outbox_row is not None
    assert outbox_row.published is False

    relay = OutboxRelay(session_factory=mock_session_factory, publisher=fake_publisher)
    await relay.process_batch()

    assert len(fake_publisher.published_messages) == 1
    published_msg = fake_publisher.published_messages[0]
    assert published_msg["routing_key"] == OutboxEventType.PAYMENTS_NEW
    assert published_msg["payload"]["payment_id"] == payment_id

    result = await db_session.execute(
        OutboxORM.__table__.select().where(
            OutboxORM.payload["payment_id"].astext == payment_id
        )
    )
    outbox_row = result.fetchone()
    assert outbox_row.published is True
