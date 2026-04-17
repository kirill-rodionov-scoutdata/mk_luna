from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.app_layer.interfaces.payments.schemas import PaymentCreateDTO
from app.app_layer.services.outbox import OutboxService
from app.app_layer.services.payment import PaymentService
from app.domain.models.payment import Currency, PaymentStatus
from tests.environment.unit_of_work import TestUow


@pytest.mark.asyncio
async def test_process_payment_succeeds(
    payment_service: PaymentService,
    outbox_service: OutboxService,
    db_session: AsyncSession,
    payment_records: list[dict[str, Any]],
) -> None:
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }
    payment = await payment_service.create_payment(PaymentCreateDTO(**kwargs))

    with patch.object(
        outbox_service, "_simulate_external_gate_processing", AsyncMock()
    ):
        with patch.object(
            outbox_service, "send_webhook_notification", AsyncMock()
        ) as mock_webhook:
            await outbox_service.process_payment(payment.id)

            async with TestUow(db_session) as uow:
                updated = await uow.payments.get(payment.id)
                assert updated.status == PaymentStatus.SUCCEEDED
                assert updated.processed_at is not None

            mock_webhook.assert_called_once()


@pytest.mark.asyncio
async def test_process_payment_fails_on_gateway_error(
    payment_service: PaymentService,
    outbox_service: OutboxService,
    db_session: AsyncSession,
    payment_records: list[dict[str, Any]],
) -> None:
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }
    payment = await payment_service.create_payment(PaymentCreateDTO(**kwargs))

    with patch.object(
        outbox_service,
        "_simulate_external_gate_processing",
        AsyncMock(side_effect=Exception("Gateway error")),
    ):
        with patch.object(outbox_service, "send_webhook_notification", AsyncMock()):
            await outbox_service.process_payment(payment.id)

            async with TestUow(db_session) as uow:
                updated = await uow.payments.get(payment.id)
                assert updated.status == PaymentStatus.FAILED


@pytest.mark.asyncio
async def test_process_payment_idempotent_if_already_processed(
    payment_service: PaymentService,
    outbox_service: OutboxService,
    db_session: AsyncSession,
    payment_records: list[dict[str, Any]],
) -> None:
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }
    payment = await payment_service.create_payment(PaymentCreateDTO(**kwargs))

    async with TestUow(db_session) as uow:
        entity = await uow.payments.get(payment.id)
        entity.status = PaymentStatus.SUCCEEDED
        await uow.payments.update(entity)

    with patch.object(
        outbox_service, "_simulate_external_gate_processing", AsyncMock()
    ) as mock_sim:
        await outbox_service.process_payment(payment.id)
        mock_sim.assert_not_called()
