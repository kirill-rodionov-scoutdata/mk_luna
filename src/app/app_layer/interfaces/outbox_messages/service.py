import uuid
from abc import ABC, abstractmethod


class AbstractOutboxService(ABC):
    @abstractmethod
    async def process_payment(self, payment_id: uuid.UUID) -> None:
        """Process a payment from an outbox event."""
        ...
