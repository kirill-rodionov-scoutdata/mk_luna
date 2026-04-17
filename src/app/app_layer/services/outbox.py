import logging
import random
import uuid
from datetime import UTC, datetime

from app.app_layer.interfaces.clients.webhook import AbstractWebhookClient
from app.app_layer.interfaces.outbox_messages.service import AbstractOutboxService
from app.app_layer.interfaces.unit_of_work.sql import AbstractUnitOfWork
from app.domain.exceptions import PaymentNotFoundError, PaymentProcessingError
from app.domain.models.payment import PaymentEntity, PaymentStatus

logger = logging.getLogger(__name__)


class OutboxService(AbstractOutboxService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        webhook_client: AbstractWebhookClient,
    ) -> None:
        self._uow = uow
        self._webhook_client = webhook_client

    async def process_payment(self, payment_id: uuid.UUID) -> None:
        """
        Business logic for processing a payment triggered by outbox event.
        """
        payment = await self._get_payment(payment_id)

        if payment.status == PaymentStatus.SUCCEEDED:
            logger.info(
                "Payment %s already processed with status %s",
                payment_id,
                payment.status,
            )
            return

        if payment.status == PaymentStatus.FAILED:
            raise PaymentProcessingError(
                str(payment_id),
                "payment is already marked as failed",
            )

        try:
            await self._simulate_external_gate_processing(payment)
        except Exception as exc:
            await self._update_status(payment_id, PaymentStatus.FAILED)
            raise PaymentProcessingError(str(payment_id), str(exc)) from exc

        payment = await self._update_status(payment_id, PaymentStatus.SUCCEEDED)
        await self.send_webhook_notification(payment)

    async def _simulate_external_gate_processing(self, payment: PaymentEntity) -> None:
        """
        MOCK: Simulates external gate processing.
        Wrapped separately to distinguish from production logic.
        """
        import asyncio

        await asyncio.sleep(random.uniform(2, 5))
        if payment.metadata.get("force_technical_error") is True:
            raise Exception("Gateway connection error (forced)")
        if random.random() < 0.1:
            raise Exception("Gateway connection error")

    async def _get_payment(self, payment_id: uuid.UUID) -> PaymentEntity:
        async with self._uow as uow:
            payment = await uow.payments.get(payment_id)

        if not payment:
            raise PaymentNotFoundError(str(payment_id))

        return payment

    async def _update_status(
        self,
        payment_id: uuid.UUID,
        status: PaymentStatus,
    ) -> PaymentEntity:
        async with self._uow as uow:
            payment = await uow.payments.get(payment_id)
            if not payment:
                raise PaymentNotFoundError(str(payment_id))

            payment.status = status
            payment.processed_at = datetime.now(UTC)
            await uow.payments.update(payment)

        return payment

    async def send_webhook_notification(self, payment: PaymentEntity) -> None:
        """
        Production-level logic for sending async webhook notification.
        """
        payload = {
            "payment_id": str(payment.id),
            "status": payment.status.value,
            "idempotency_key": payment.idempotency_key,
        }
        await self._webhook_client.send_notification(
            url=payment.webhook_url, payload=payload
        )
