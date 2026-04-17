from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.app_layer.interfaces.unit_of_work.sql import AbstractUnitOfWork
from app.infra.repositories.outbox_repository import SqlAlchemyOutboxRepository
from app.infra.repositories.payment_repository import PaymentsRepository


class AlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> Self:
        self.session: AsyncSession = self.session_factory()
        self.payments = PaymentsRepository(self.session)
        self.outbox = SqlAlchemyOutboxRepository(self.session)
        return await super().__aenter__()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def shutdown(self) -> None:
        await self.session.close()
