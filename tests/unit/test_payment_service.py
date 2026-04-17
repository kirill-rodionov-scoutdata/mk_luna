import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.app_layer.interfaces.payments.schemas import PaymentCreateDTO
from app.app_layer.services.payment import PaymentService
from app.domain.exceptions import PaymentNotFoundError
from app.domain.models.outbox import OutboxEventType
from app.domain.models.payment import Currency, PaymentStatus
from tests.environment.unit_of_work import TestUow


async def test_create_payment_returns_new_payment(
    payment_service: PaymentService,
    payment_records: list[dict[str, Any]],
) -> None:
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    payment = await payment_service.create_payment(PaymentCreateDTO(**kwargs))

    assert payment.idempotency_key == record["idempotency_key"]
    assert payment.amount == Decimal(record["amount"])
    assert payment.currency == record["currency"]
    assert payment.status == PaymentStatus.PENDING
    assert payment.id is not None


async def test_create_payment_persists_to_repository(
    db_session: AsyncSession,
    payment_service: PaymentService,
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
        stored = await uow.payments.get(payment.id)
    assert stored is not None
    assert stored.id == payment.id


async def test_create_payment_is_idempotent(
    payment_service: PaymentService,
    payment_records: list[dict[str, Any]],
) -> None:
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    first = await payment_service.create_payment(PaymentCreateDTO(**kwargs))
    second = await payment_service.create_payment(PaymentCreateDTO(**kwargs))

    assert first.id == second.id


async def test_create_payment_adds_outbox_event(
    db_session: AsyncSession,
    payment_service: PaymentService,
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
        events = await uow.outbox.get_unpublished()
    assert len(events) == 1
    assert events[0].event_type == OutboxEventType.PAYMENTS_NEW
    assert events[0].payload == {"payment_id": str(payment.id)}


async def test_create_payment_idempotent_does_not_add_extra_outbox_event(
    db_session: AsyncSession,
    payment_service: PaymentService,
    payment_records: list[dict[str, Any]],
) -> None:
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    await payment_service.create_payment(PaymentCreateDTO(**kwargs))
    await payment_service.create_payment(PaymentCreateDTO(**kwargs))

    async with TestUow(db_session) as uow:
        events = await uow.outbox.get_unpublished()
    assert len(events) == 1


async def test_get_payment_returns_existing(
    payment_service: PaymentService,
    payment_records: list[dict[str, Any]],
) -> None:
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }
    created = await payment_service.create_payment(PaymentCreateDTO(**kwargs))

    fetched = await payment_service.get_payment(created.id)

    assert fetched.id == created.id
    assert fetched.idempotency_key == record["idempotency_key"]


async def test_get_payment_raises_not_found_for_unknown_id(
    payment_service: PaymentService,
) -> None:
    unknown_id = uuid.uuid4()

    with pytest.raises(PaymentNotFoundError):
        await payment_service.get_payment(unknown_id)


async def test_create_payment_with_metadata(
    payment_service: PaymentService,
    payment_records: list[dict[str, Any]],
) -> None:
    record = payment_records[2]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    payment = await payment_service.create_payment(PaymentCreateDTO(**kwargs))

    assert payment.metadata == record["metadata"]
