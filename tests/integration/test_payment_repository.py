import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DuplicateIdempotencyKeyError
from app.domain.models.outbox import OutboxEventType
from app.domain.models.payment import PaymentEntity, PaymentStatus
from app.infra.repositories.outbox_repository import SqlAlchemyOutboxRepository
from app.infra.repositories.payment_repository import PaymentsRepository
from tests.satellites import make_payment_entity


async def test_add_and_get_payment(
    db_session: AsyncSession,
    payment_entity: PaymentEntity,
) -> None:
    repo = PaymentsRepository(db_session)

    await repo.add(payment_entity)
    await db_session.flush()

    fetched = await repo.get(payment_entity.id)
    assert fetched is not None
    assert fetched.id == payment_entity.id
    assert fetched.amount == payment_entity.amount
    assert fetched.currency == payment_entity.currency


async def test_get_returns_none_for_unknown_id(db_session: AsyncSession) -> None:
    repo = PaymentsRepository(db_session)

    result = await repo.get(uuid.uuid4())

    assert result is None


async def test_get_by_idempotency_key(
    db_session: AsyncSession,
    payment_entity: PaymentEntity,
) -> None:
    repo = PaymentsRepository(db_session)
    await repo.add(payment_entity)
    await db_session.flush()

    fetched = await repo.get_by_idempotency_key(payment_entity.idempotency_key)

    assert fetched is not None
    assert fetched.id == payment_entity.id


async def test_get_by_idempotency_key_returns_none_if_missing(
    db_session: AsyncSession,
) -> None:
    repo = PaymentsRepository(db_session)

    result = await repo.get_by_idempotency_key("nonexistent-key")

    assert result is None


async def test_update_payment_status(
    db_session: AsyncSession,
    payment_entity: PaymentEntity,
) -> None:
    repo = PaymentsRepository(db_session)
    await repo.add(payment_entity)
    await db_session.flush()

    payment_entity = payment_entity.model_copy(
        update={"status": PaymentStatus.SUCCEEDED}
    )

    await repo.update(payment_entity)
    await db_session.flush()

    fetched = await repo.get(payment_entity.id)
    assert fetched.status == PaymentStatus.SUCCEEDED


async def test_idempotency_key_unique_constraint(
    db_session: AsyncSession,
    payment_records: list[dict[str, Any]],
) -> None:
    repo = PaymentsRepository(db_session)
    record = payment_records[0]
    p1 = make_payment_entity(record)
    p2 = make_payment_entity(record)

    await repo.add(p1)

    with pytest.raises(DuplicateIdempotencyKeyError):
        await repo.add(p2)


async def test_payment_metadata_stored_as_jsonb(
    db_session: AsyncSession,
    payment_records: list[dict[str, Any]],
) -> None:
    repo = PaymentsRepository(db_session)
    record = payment_records[4]
    payment = make_payment_entity(record)

    await repo.add(payment)
    await db_session.flush()

    fetched = await repo.get(payment.id)
    assert fetched.metadata == record["metadata"]


async def test_outbox_add_and_get_unpublished(db_session: AsyncSession) -> None:
    repo = SqlAlchemyOutboxRepository(db_session)

    await repo.add(OutboxEventType.PAYMENTS_NEW, {"payment_id": str(uuid.uuid4())})
    await db_session.flush()

    events = await repo.get_unpublished()
    assert len(events) >= 1
    assert events[-1].event_type == OutboxEventType.PAYMENTS_NEW


async def test_outbox_mark_published(db_session: AsyncSession) -> None:
    repo = SqlAlchemyOutboxRepository(db_session)
    payment_id = str(uuid.uuid4())

    await repo.add(OutboxEventType.PAYMENTS_NEW, {"payment_id": payment_id})
    await db_session.flush()

    events = await repo.get_unpublished()
    target = next(e for e in events if e.payload.get("payment_id") == payment_id)

    await repo.mark_published(target.id)
    await db_session.flush()

    remaining = await repo.get_unpublished()
    ids = [e.id for e in remaining]
    assert target.id not in ids
