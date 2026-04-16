"""
PaymentService — application use-case orchestrator.

Depends only on abstract interfaces; never imports SQLAlchemy or FastStream.
The container wires concrete implementations at startup.
"""

import uuid

from app.app_layer.interfaces.rabbit.event_publisher import AbstractEventPublisher
from app.app_layer.interfaces.unit_of_work.sql import AbstractUnitOfWork
from app.domain.exceptions import DuplicateIdempotencyKeyError, PaymentNotFoundError
from app.domain.models.payment import Currency, Payment


class PaymentService:
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        publisher: AbstractEventPublisher,
    ) -> None:
        self._uow = uow
        self._publisher = publisher

    async def create_payment(
        self,
        *,
        idempotency_key: str,
        amount,
        currency: Currency,
        description: str,
        metadata: dict,
        webhook_url: str,
    ) -> Payment:
        """
        Create a new payment and enqueue it for processing.

        Idempotent: returns existing payment if idempotency_key already used.
        Publishes a 'payments.new' event via the Outbox pattern.
        """
        async with self._uow as uow:
            existing = await uow.payments.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing

            payment = Payment(
                amount=amount,
                currency=currency,
                description=description,
                metadata=metadata,
                idempotency_key=idempotency_key,
                webhook_url=webhook_url,
            )

            await uow.payments.add(payment)

            # Outbox: write event atomically with the payment record
            await uow.outbox.add(
                event_type="payments.new",
                payload={"payment_id": str(payment.id)},
            )

        return payment

    async def get_payment(self, payment_id: uuid.UUID) -> Payment:
        """Return a payment by ID. Raises PaymentNotFoundError if absent."""
        async with self._uow as uow:
            payment = await uow.payments.get(payment_id)

        if payment is None:
            raise PaymentNotFoundError(str(payment_id))

        return payment
