import uuid
from abc import ABC, abstractmethod

from app.app_layer.interfaces.repositories.outbox.dto import OutboxEventDTO
from app.domain.models.outbox import OutboxEventType


class AbstractOutboxRepository(ABC):
    """Defines the persistence contract for Outbox events."""

    @abstractmethod
    async def add(self, event_type: OutboxEventType, payload: dict) -> None:
        """Write a new outbox record (unpublished event)."""
        ...

    @abstractmethod
    async def get_unpublished(self, limit: int = 100) -> list[OutboxEventDTO]:
        """Return unpublished outbox records for the relay loop."""
        ...

    @abstractmethod
    async def mark_published(self, event_id: uuid.UUID) -> None:
        """Mark an outbox record as successfully published."""
        ...
