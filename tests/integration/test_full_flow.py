import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.models.outbox import OutboxEventType
from app.domain.models.payment import PaymentStatus
from app.infra.db.models import OutboxORM, PaymentORM
from app.infra.rabbitmq.outbox_relay import OutboxRelay


@pytest.mark.asyncio
async def test_full_payment_flow(client, db_session, fake_publisher, payment_records, engine):
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    record = payment_records[0].copy()
    headers = {"Idempotency-Key": str(record.pop("idempotency_key"))}

    response = await client.post("/api/v1/payments", json=record, headers=headers)
    
    assert response.status_code == 202
    data = response.json()
    assert "payment_id" in data
    payment_id = data["payment_id"]
    
    async with session_factory() as session:
        payment = await session.get(PaymentORM, payment_id)
        assert payment is not None
        assert payment.status == PaymentStatus.PENDING.value
        
        result = await session.execute(
            OutboxORM.__table__.select().where(OutboxORM.payload["payment_id"].astext == payment_id)
        )
        outbox_row = result.fetchone()
        assert outbox_row is not None
        assert outbox_row.published is False

    relay = OutboxRelay(session_factory=session_factory, publisher=fake_publisher)
    await relay.process_batch()
    
    assert len(fake_publisher.published_messages) == 1
    published_msg = fake_publisher.published_messages[0]
    assert published_msg["routing_key"] == OutboxEventType.PAYMENTS_NEW
    assert published_msg["payload"]["payment_id"] == payment_id

    async with session_factory() as session:
        result = await session.execute(
            OutboxORM.__table__.select().where(OutboxORM.payload["payment_id"].astext == payment_id)
        )
        outbox_row = result.fetchone()
        assert outbox_row.published is True
