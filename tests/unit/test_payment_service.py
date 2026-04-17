import uuid
from decimal import Decimal

import pytest

from app.domain.exceptions import PaymentNotFoundError
from app.domain.models.payment import Currency, PaymentStatus
from tests.environment.unit_of_work import TestUow


async def test_create_payment_returns_new_payment(payment_service, payment_records):
    
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    
    payment = await payment_service.create_payment(**kwargs)

    
    assert payment.idempotency_key == record["idempotency_key"]
    assert payment.amount == Decimal(record["amount"])
    assert payment.currency == record["currency"]
    assert payment.status == PaymentStatus.PENDING
    assert payment.id is not None


async def test_create_payment_persists_to_repository(db_session, payment_service, payment_records):
    
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    
    payment = await payment_service.create_payment(**kwargs)

    
    async with TestUow(db_session) as uow:
        stored = await uow.payments.get(payment.id)
    assert stored is not None
    assert stored.id == payment.id


async def test_create_payment_is_idempotent(payment_service, payment_records):
    
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    
    first = await payment_service.create_payment(**kwargs)
    second = await payment_service.create_payment(**kwargs)

    
    assert first.id == second.id


async def test_create_payment_adds_outbox_event(db_session, payment_service, payment_records):
    
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    
    payment = await payment_service.create_payment(**kwargs)

    
    async with TestUow(db_session) as uow:
        events = await uow.outbox.get_unpublished()
    assert len(events) == 1
    assert events[0].event_type == "payments.new"
    assert events[0].payload == {"payment_id": str(payment.id)}


async def test_create_payment_idempotent_does_not_add_extra_outbox_event(
    db_session, payment_service, payment_records
):
    
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    
    await payment_service.create_payment(**kwargs)
    await payment_service.create_payment(**kwargs)

    
    async with TestUow(db_session) as uow:
        events = await uow.outbox.get_unpublished()
    assert len(events) == 1


async def test_get_payment_returns_existing(payment_service, payment_records):
    
    record = payment_records[0]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }
    created = await payment_service.create_payment(**kwargs)

    
    fetched = await payment_service.get_payment(created.id)

    
    assert fetched.id == created.id
    assert fetched.idempotency_key == record["idempotency_key"]


async def test_get_payment_raises_not_found_for_unknown_id(payment_service):
    
    unknown_id = uuid.uuid4()

     # Assert
    with pytest.raises(PaymentNotFoundError):
        await payment_service.get_payment(unknown_id)


async def test_create_payment_with_metadata(payment_service, payment_records):
    
    # Use record with rich metadata
    record = payment_records[2]
    kwargs = {
        **record,
        "amount": Decimal(record["amount"]),
        "currency": Currency(record["currency"]),
    }

    
    payment = await payment_service.create_payment(**kwargs)

    
    assert payment.metadata == record["metadata"]
