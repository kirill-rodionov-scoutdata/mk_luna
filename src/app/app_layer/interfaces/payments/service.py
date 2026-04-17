import uuid
from abc import ABC, abstractmethod

from app.app_layer.interfaces.payments.schemas import (
    PaymentCreateDTO,
    PaymentOutputDTO,
)


class AbstractPaymentService(ABC):
    @abstractmethod
    async def create_payment(self, dto: PaymentCreateDTO) -> PaymentOutputDTO:
        """Create a new payment."""
        ...

    @abstractmethod
    async def get_payment(self, payment_id: uuid.UUID) -> PaymentOutputDTO:
        """Get a payment by ID."""
        ...
