"""
Tests for PaymentService.

Each test runs against real SQLAlchemy repositories backed by a savepoint-isolated
db_session (rolled back after the test completes — no permanent DB side effects).
"""

import uuid
from decimal import Decimal

import pytest

from app.app_layer.services.payment import PaymentService
from app.domain.exceptions import PaymentNotFoundError
from app.domain.models.payment import Currency, PaymentStatus
from tests.environment.unit_of_work import TestUow


def _make_service(uow: TestUow) -> PaymentService:
    return PaymentService(uow=uow, on_outbox_write=lambda: None)


_PAYMENT_KWARGS = dict(
    idempotency_key="key-abc",
    amount=Decimal("100.00"),
    currency=Currency.RUB,
    description="test payment",
    metadata={},
    webhook_url="http://example.com/hook",
)


async def test_create_payment_returns_new_payment(db_session):
    service = _make_service(TestUow(db_session))

    payment = await service.create_payment(**_PAYMENT_KWARGS)

    assert payment.idempotency_key == "key-abc"
    assert payment.amount == Decimal("100.00")
    assert payment.currency == Currency.RUB
    assert payment.status == PaymentStatus.PENDING
    assert payment.id is not None


async def test_create_payment_persists_to_repository(db_session):
    service = _make_service(TestUow(db_session))

    payment = await service.create_payment(**_PAYMENT_KWARGS)

    async with TestUow(db_session) as uow:
        stored = await uow.payments.get(payment.id)
    assert stored is not None
    assert stored.id == payment.id


async def test_create_payment_is_idempotent(db_session):
    service = _make_service(TestUow(db_session))

    first = await service.create_payment(**_PAYMENT_KWARGS)
    second = await service.create_payment(**_PAYMENT_KWARGS)

    assert first.id == second.id


async def test_create_payment_adds_outbox_event(db_session):
    service = _make_service(TestUow(db_session))

    payment = await service.create_payment(**_PAYMENT_KWARGS)

    async with TestUow(db_session) as uow:
        events = await uow.outbox.get_unpublished()
    assert len(events) == 1
    assert events[0].event_type == "payments.new"
    assert events[0].payload == {"payment_id": str(payment.id)}


async def test_create_payment_idempotent_does_not_add_extra_outbox_event(db_session):
    service = _make_service(TestUow(db_session))

    await service.create_payment(**_PAYMENT_KWARGS)
    await service.create_payment(**_PAYMENT_KWARGS)

    async with TestUow(db_session) as uow:
        events = await uow.outbox.get_unpublished()
    assert len(events) == 1


async def test_get_payment_returns_existing(db_session):
    service = _make_service(TestUow(db_session))
    created = await service.create_payment(**_PAYMENT_KWARGS)

    fetched = await service.get_payment(created.id)

    assert fetched.id == created.id
    assert fetched.idempotency_key == "key-abc"


async def test_get_payment_raises_not_found_for_unknown_id(db_session):
    service = _make_service(TestUow(db_session))

    with pytest.raises(PaymentNotFoundError):
        await service.get_payment(uuid.uuid4())


async def test_create_payment_with_metadata(db_session):
    service = _make_service(TestUow(db_session))
    meta = {"order_id": "ord-1", "user_id": 42}

    payment = await service.create_payment(
        **{**_PAYMENT_KWARGS, "metadata": meta, "idempotency_key": "key-meta"}
    )

    assert payment.metadata == meta
