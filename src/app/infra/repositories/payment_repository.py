"""
SQLAlchemy implementation of AbstractPaymentRepository.

Maps between the ORM model (PaymentORM) and the domain model (PaymentEntity).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.app_layer.interfaces.repositories import AbstractPaymentRepository
from app.domain.exceptions import DuplicateIdempotencyKeyError
from app.domain.models.payment import PaymentEntity
from app.infra.db.models import PaymentORM


class PaymentsRepository(AbstractPaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, payment: PaymentEntity) -> None:
        self._session.add(payment.to_orm())
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateIdempotencyKeyError(payment.idempotency_key) from exc

    async def get(self, payment_id: uuid.UUID) -> PaymentEntity | None:
        result = await self._session.get(PaymentORM, payment_id)
        return PaymentEntity.from_orm(result) if result else None

    async def get_by_idempotency_key(self, key: str) -> PaymentEntity | None:
        stmt = select(PaymentORM).where(PaymentORM.idempotency_key == key)
        result = await self._session.scalar(stmt)
        return PaymentEntity.from_orm(result) if result else None

    async def update(self, payment: PaymentEntity) -> None:
        stmt = select(PaymentORM).where(PaymentORM.id == payment.id)
        row = await self._session.scalar(stmt)
        if row:
            row.status = payment.status.value
            row.processed_at = payment.processed_at
