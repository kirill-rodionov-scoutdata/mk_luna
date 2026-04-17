from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.models.payment import Currency, PaymentStatus
from tests.environment.unit_of_work import TestUow


@pytest.mark.asyncio
async def test_process_payment_succeeds(
    payment_service, outbox_service, db_session, payment_records
):
    # Setup: Create a pending payment via payment_service
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }
    payment = await payment_service.create_payment(**kwargs)

    # Mock simulation to succeed and webhook to not fail in outbox_service
    with patch.object(
        outbox_service, "_simulate_external_gate_processing", AsyncMock()
    ):
        with patch.object(
            outbox_service, "send_webhook_notification", AsyncMock()
        ) as mock_webhook:
            # Action: Process via outbox_service
            await outbox_service.process_payment(payment.id)

            # Assert DB update
            async with TestUow(db_session) as uow:
                updated = await uow.payments.get(payment.id)
                assert updated.status == PaymentStatus.SUCCEEDED
                assert updated.processed_at is not None

            # Assert webhook called
            mock_webhook.assert_called_once()


@pytest.mark.asyncio
async def test_process_payment_fails_on_gateway_error(
    payment_service, outbox_service, db_session, payment_records
):
    # Setup
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }
    payment = await payment_service.create_payment(**kwargs)

    # Mock simulation to fail
    with patch.object(
        outbox_service,
        "_simulate_external_gate_processing",
        AsyncMock(side_effect=Exception("Gateway error")),
    ):
        with patch.object(outbox_service, "send_webhook_notification", AsyncMock()):
            # Action
            await outbox_service.process_payment(payment.id)

            # Assert DB update
            async with TestUow(db_session) as uow:
                updated = await uow.payments.get(payment.id)
                assert updated.status == PaymentStatus.FAILED


@pytest.mark.asyncio
async def test_process_payment_idempotent_if_already_processed(
    payment_service, outbox_service, db_session, payment_records
):
    # Setup: Already processed
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }
    payment = await payment_service.create_payment(**kwargs)

    async with TestUow(db_session) as uow:
        payment.status = PaymentStatus.SUCCEEDED
        await uow.payments.update(payment)

    # Action: Try processing again
    with patch.object(
        outbox_service, "_simulate_external_gate_processing", AsyncMock()
    ) as mock_sim:
        await outbox_service.process_payment(payment.id)
        # Should NOT call simulation again
        mock_sim.assert_not_called()
