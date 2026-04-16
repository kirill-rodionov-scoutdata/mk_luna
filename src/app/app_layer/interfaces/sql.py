"""
Abstract Unit of Work interface.

Wraps a single database transaction. All repositories are accessed
through the UoW so that they share the same session/transaction.

Usage:
    async with uow:
        await uow.payments.add(payment)
        await uow.outbox.add("payment.created", payload)
        # commit happens automatically on __aexit__ (no exception)
"""

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
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
