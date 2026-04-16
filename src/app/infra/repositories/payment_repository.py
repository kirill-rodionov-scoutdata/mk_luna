"""
SQLAlchemy implementation of AbstractPaymentRepository.

Maps between the ORM model (PaymentORM) and the domain model (Payment).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.app_layer.interfaces.repositories import AbstractPaymentRepository
from app.domain.models.payment import Currency, Payment, PaymentStatus
from app.infra.db.models import PaymentORM


def _orm_to_domain(row: PaymentORM) -> Payment:
    return Payment(
        id=row.id,
        amount=row.amount,
        currency=Currency(row.currency),
        description=row.description,
        metadata=row.metadata_,
        status=PaymentStatus(row.status),
        idempotency_key=row.idempotency_key,
        webhook_url=row.webhook_url,
        created_at=row.created_at,
        processed_at=row.processed_at,
    )


def _domain_to_orm(payment: Payment) -> PaymentORM:
    return PaymentORM(
        id=payment.id,
        amount=payment.amount,
        currency=payment.currency.value,
        description=payment.description,
        metadata_=payment.metadata,
        status=payment.status.value,
        idempotency_key=payment.idempotency_key,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )


class SqlAlchemyPaymentRepository(AbstractPaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, payment: Payment) -> None:
        orm_obj = _domain_to_orm(payment)
        self._session.add(orm_obj)

    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        result = await self._session.get(PaymentORM, payment_id)
        return _orm_to_domain(result) if result else None

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        stmt = select(PaymentORM).where(PaymentORM.idempotency_key == key)
        result = await self._session.scalar(stmt)
        return _orm_to_domain(result) if result else None

    async def update(self, payment: Payment) -> None:
        stmt = select(PaymentORM).where(PaymentORM.id == payment.id)
        row = await self._session.scalar(stmt)
        if row:
            row.status = payment.status.value
            row.processed_at = payment.processed_at
