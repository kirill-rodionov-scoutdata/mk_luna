"""
SQLAlchemy implementation of the Unit of Work pattern.

One instance = one database transaction.
Both repositories share the same AsyncSession so they participate
in the same transaction and commit/rollback atomically.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.app_layer.interfaces.unit_of_work import AbstractUnitOfWork
from app.infra.repositories.outbox_repository import SqlAlchemyOutboxRepository
from app.infra.repositories.payment_repository import SqlAlchemyPaymentRepository


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self):
        self._session: AsyncSession = self._session_factory()
        self.payments = SqlAlchemyPaymentRepository(self._session)
        self.outbox = SqlAlchemyOutboxRepository(self._session)
        return await super().__aenter__()

    async def __aexit__(self, *args):
        await super().__aexit__(*args)
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
