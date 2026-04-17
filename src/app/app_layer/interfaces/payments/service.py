import uuid
from abc import ABC, abstractmethod
from decimal import Decimal

from app.domain.models.payment import Currency, PaymentEntity


class AbstractPaymentService(ABC):
    @abstractmethod
    async def create_payment(
        self,
        *,
        idempotency_key: str,
        amount: Decimal,
        currency: Currency,
        description: str,
        metadata: dict,
        webhook_url: str,
    ) -> PaymentEntity:
        """Create a new payment."""
        ...

    @abstractmethod
    async def get_payment(self, payment_id: uuid.UUID) -> PaymentEntity:
        """Get a payment by ID."""
        ...
