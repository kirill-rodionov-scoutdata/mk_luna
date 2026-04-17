from unittest.mock import AsyncMock

import pytest

from app.app_layer.interfaces.clients.webhook import AbstractWebhookClient
from app.app_layer.services.outbox import OutboxService
from app.domain.models.payment import Currency, PaymentEntity, PaymentStatus
from app.infra.unit_of_work.alchemy import AlchemyUnitOfWork
from tests.environment.unit_of_work import TestUow


class FakeWebhookClient(AbstractWebhookClient):
    def __init__(self):
        self.notifications_sent = 0

    async def send_notification(self, url: str, payload: dict) -> None:
        self.notifications_sent += 1


@pytest.mark.asyncio
async def test_consumer_idempotency_keeps_status(db_session, payment_records):
    uow = TestUow(db_session)
    webhook_client = FakeWebhookClient()
    service = OutboxService(uow=uow, webhook_client=webhook_client)
    record = payment_records[0]
    payment = PaymentEntity(
        amount=record["amount"],
        currency=Currency(record["currency"]),
        description=record["description"],
        metadata=record["metadata"],
        idempotency_key=record["idempotency_key"],
        webhook_url=record["webhook_url"],
    )
    async with uow as u:
        await u.payments.add(payment)
        await u.commit()

    service._simulate_external_gate_processing = AsyncMock()

    await service.process_payment(payment.id)
    
    service._simulate_external_gate_processing.assert_called_once()
    assert webhook_client.notifications_sent == 1
    
    async with uow as u:
        updated_payment = await u.payments.get(payment.id)
        assert updated_payment.status == PaymentStatus.SUCCEEDED

    await service.process_payment(payment.id)

    service._simulate_external_gate_processing.assert_called_once()
    assert webhook_client.notifications_sent == 1
