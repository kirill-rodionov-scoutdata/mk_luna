import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.models.payment import Currency, PaymentEntity, PaymentStatus
from app.infra.repositories.outbox_repository import SqlAlchemyOutboxRepository
from app.infra.repositories.payment_repository import PaymentsRepository

def _make_payment(idempotency_key: str = "key-001", **overrides) -> PaymentEntity:
    defaults = dict(
        amount=Decimal("250.00"),
        currency=Currency.USD,
        description="integration test",
        metadata={"source": "test"},
        idempotency_key=idempotency_key,
        webhook_url="http://example.com/hook",
    )
    return PaymentEntity(**{**defaults, **overrides})


async def test_add_and_get_payment(db_session):
    repo = PaymentsRepository(db_session)
    payment = _make_payment()

    await repo.add(payment)
    await db_session.flush()

    fetched = await repo.get(payment.id)
    assert fetched is not None
    assert fetched.id == payment.id
    assert fetched.amount == Decimal("250.00")
    assert fetched.currency == Currency.USD


async def test_get_returns_none_for_unknown_id(db_session):
    repo = PaymentsRepository(db_session)

    result = await repo.get(uuid.uuid4())

    assert result is None


async def test_get_by_idempotency_key(db_session):
    repo = PaymentsRepository(db_session)
    payment = _make_payment(idempotency_key="idem-xyz")

    await repo.add(payment)
    await db_session.flush()

    fetched = await repo.get_by_idempotency_key("idem-xyz")
    assert fetched is not None
    assert fetched.id == payment.id


async def test_get_by_idempotency_key_returns_none_if_missing(db_session):
    repo = PaymentsRepository(db_session)

    result = await repo.get_by_idempotency_key("nonexistent-key")

    assert result is None


async def test_update_payment_status(db_session):
    repo = PaymentsRepository(db_session)
    payment = _make_payment(idempotency_key="key-update")

    await repo.add(payment)
    await db_session.flush()

    payment = payment.model_copy(update={"status": PaymentStatus.SUCCEEDED})
    await repo.update(payment)
    await db_session.flush()

    fetched = await repo.get(payment.id)
    assert fetched.status == PaymentStatus.SUCCEEDED


async def test_idempotency_key_unique_constraint(db_session):
    repo = PaymentsRepository(db_session)
    key = "unique-key-test"

    await repo.add(_make_payment(idempotency_key=key))
    await db_session.flush()

    await repo.add(_make_payment(idempotency_key=key))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_payment_metadata_stored_as_jsonb(db_session):
    repo = PaymentsRepository(db_session)
    meta = {"nested": {"foo": 1}, "tags": ["a", "b"]}
    payment = _make_payment(idempotency_key="key-json", metadata=meta)

    await repo.add(payment)
    await db_session.flush()

    fetched = await repo.get(payment.id)
    assert fetched.metadata == meta


async def test_outbox_add_and_get_unpublished(db_session):
    repo = SqlAlchemyOutboxRepository(db_session)

    await repo.add("payments.new", {"payment_id": str(uuid.uuid4())})
    await db_session.flush()

    events = await repo.get_unpublished()
    assert len(events) >= 1
    assert events[-1].event_type == "payments.new"


async def test_outbox_mark_published(db_session):
    repo = SqlAlchemyOutboxRepository(db_session)
    payment_id = str(uuid.uuid4())

    await repo.add("payments.new", {"payment_id": payment_id})
    await db_session.flush()

    events = await repo.get_unpublished()
    target = next(e for e in events if e.payload.get("payment_id") == payment_id)

    await repo.mark_published(target.id)
    await db_session.flush()

    remaining = await repo.get_unpublished()
    ids = [e.id for e in remaining]
    assert target.id not in ids
