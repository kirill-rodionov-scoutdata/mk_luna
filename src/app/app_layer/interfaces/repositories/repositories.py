"""
Abstract repository interfaces.

The app_layer only knows these ABCs — never the SQLAlchemy implementations.
Concrete implementations live in infra/repositories/.
"""

import uuid
from abc import ABC, abstractmethod

from app.domain.models.payment import Payment


class AbstractPaymentRepository(ABC):
    """Defines the persistence contract for Payment aggregates."""

    @abstractmethod
    async def add(self, payment: Payment) -> None:
        """Persist a new payment."""
        ...

    @abstractmethod
    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        """Return a payment by its ID, or None if not found."""
        ...

    @abstractmethod
    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        """Return a payment by idempotency key, or None if not found."""
        ...

    @abstractmethod
    async def update(self, payment: Payment) -> None:
        """Persist changes to an existing payment."""
        ...


class AbstractOutboxRepository(ABC):
    """Defines the persistence contract for Outbox events."""

    @abstractmethod
    async def add(self, event_type: str, payload: dict) -> None:
        """Write a new outbox record (unpublished event)."""
        ...

    @abstractmethod
    async def get_unpublished(self, limit: int = 100) -> list[dict]:
        """Return unpublished outbox records for the relay loop."""
        ...

    @abstractmethod
    async def mark_published(self, event_id: uuid.UUID) -> None:
        """Mark an outbox record as successfully published."""
        ...
