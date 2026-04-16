from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from app.app_layer.interfaces.repositories import (
    AbstractOutboxRepository,
    AbstractPaymentRepository,
)


class AbstractUnitOfWork(ABC):
    payments: AbstractPaymentRepository
    outbox: AbstractOutboxRepository

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.shutdown()

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def shutdown(self) -> None: ...
