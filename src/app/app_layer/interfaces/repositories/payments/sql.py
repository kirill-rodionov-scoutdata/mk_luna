import uuid
from abc import ABC, abstractmethod

from app.domain.models.payment import PaymentEntity


class AbstractPaymentRepository(ABC):
    """Defines the persistence contract for PaymentEntity aggregates."""

    @abstractmethod
    async def add(self, payment: PaymentEntity) -> None:
        """Persist a new payment."""
        ...

    @abstractmethod
    async def get(self, payment_id: uuid.UUID) -> PaymentEntity | None:
        """Return a payment by its ID, or None if not found."""
        ...

    @abstractmethod
    async def get_by_idempotency_key(self, key: str) -> PaymentEntity | None:
        """Return a payment by idempotency key, or None if not found."""
        ...

    @abstractmethod
    async def update(self, payment: PaymentEntity) -> None:
        """Persist changes to an existing payment."""
        ...
