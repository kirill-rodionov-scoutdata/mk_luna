"""
PaymentService — application use-case orchestrator.

Depends only on abstract interfaces; never imports SQLAlchemy or FastStream.
The container wires concrete implementations at startup.
"""

import uuid
from collections.abc import Callable
from decimal import Decimal

from app.app_layer.interfaces.unit_of_work.sql import AbstractUnitOfWork
from app.domain.exceptions import PaymentNotFoundError
from app.domain.models.payment import Currency, PaymentEntity


class PaymentService:
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        on_outbox_write: Callable[[], None] = lambda: None,
    ) -> None:
        self._uow = uow
        self._on_outbox_write = on_outbox_write

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
        async with self._uow as uow:
            existing = await uow.payments.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing

            payment = PaymentEntity(
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

        # Wake up the relay immediately so the event is published without delay
        self._on_outbox_write()

        return payment

    async def get_payment(self, payment_id: uuid.UUID) -> PaymentEntity:
        """Return a payment by ID. Raises PaymentNotFoundError if absent."""
        async with self._uow as uow:
            payment = await uow.payments.get(payment_id)

        if payment is None:
            raise PaymentNotFoundError(str(payment_id))

        return payment
