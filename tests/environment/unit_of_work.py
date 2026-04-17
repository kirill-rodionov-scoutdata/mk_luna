from sqlalchemy.ext.asyncio import AsyncSession

from app.app_layer.interfaces.unit_of_work.sql import AbstractUnitOfWork
from app.infra.repositories.outbox_repository import SqlAlchemyOutboxRepository
from app.infra.repositories.payment_repository import PaymentsRepository


class TestUow(AbstractUnitOfWork):
    """Unit of Work backed by a real DB session managed by the db_session fixture.

    commit() releases a savepoint (not a real commit).
    shutdown() is a no-op — the fixture owns the session lifecycle.
    """

    __test__ = False

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self):
        self.payments = PaymentsRepository(self._session)
        self.outbox = SqlAlchemyOutboxRepository(self._session)
        return self

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def shutdown(self) -> None:
        pass
