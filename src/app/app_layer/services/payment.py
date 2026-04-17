import uuid
from collections.abc import Callable

from app.app_layer.interfaces.payments.schemas import (
    PaymentCreateDTO,
    PaymentOutputDTO,
)
from app.app_layer.interfaces.payments.service import AbstractPaymentService
from app.app_layer.interfaces.unit_of_work.sql import AbstractUnitOfWork
from app.domain.exceptions import DuplicateIdempotencyKeyError, PaymentNotFoundError
from app.domain.models.outbox import OutboxEventType
from app.domain.models.payment import PaymentEntity


class PaymentService(AbstractPaymentService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        on_outbox_write: Callable[[], None] = lambda: None,
    ) -> None:
        self._uow = uow
        self._on_outbox_write = on_outbox_write

    async def create_payment(self, dto: PaymentCreateDTO) -> PaymentOutputDTO:
        async with self._uow as uow:
            existing = await uow.payments.get_by_idempotency_key(dto.idempotency_key)
            if existing:
                raise DuplicateIdempotencyKeyError(dto.idempotency_key)

            payment = PaymentEntity(
                amount=dto.amount,
                currency=dto.currency,
                description=dto.description,
                metadata=dto.metadata,
                idempotency_key=dto.idempotency_key,
                webhook_url=dto.webhook_url,
            )

            await uow.payments.add(payment)

            await uow.outbox.add(
                event_type=OutboxEventType.PAYMENTS_NEW,
                payload={"payment_id": str(payment.id)},
            )

        self._on_outbox_write()

        return payment.to_dto()

    async def get_payment(self, payment_id: uuid.UUID) -> PaymentOutputDTO:
        async with self._uow as uow:
            payment = await uow.payments.get(payment_id)

        if payment is None:
            raise PaymentNotFoundError(str(payment_id))

        return payment.to_dto()
