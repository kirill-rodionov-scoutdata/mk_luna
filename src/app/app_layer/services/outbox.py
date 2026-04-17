import logging
import uuid
from datetime import UTC, datetime

from app.app_layer.interfaces.clients.webhook import AbstractWebhookClient
from app.app_layer.interfaces.outbox_messages.service import AbstractOutboxService
from app.app_layer.interfaces.unit_of_work.sql import AbstractUnitOfWork
from app.domain.exceptions import PaymentNotFoundError
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
        async with self._uow as uow:
            payment = await uow.payments.get(payment_id)
            if not payment:
                raise PaymentNotFoundError(str(payment_id))

            if payment.status != PaymentStatus.PENDING:
                logger.info(
                    "Payment %s already processed with status %s",
                    payment_id,
                    payment.status,
                )
                return

            try:
                await self._simulate_external_gate_processing()
                payment.status = PaymentStatus.SUCCEEDED
            except Exception as exc:
                logger.warning(
                    "Simulated gate failure for payment %s: %s", payment_id, exc
                )
                payment.status = PaymentStatus.FAILED

            payment.processed_at = datetime.now(UTC)
            await uow.payments.update(payment)

        await self.send_webhook_notification(payment)

    async def _simulate_external_gate_processing(self) -> None:
        """
        MOCK: Simulates external gate processing.
        Wrapped separately to distinguish from production logic.
        """
        import asyncio
        import random

        await asyncio.sleep(random.uniform(2, 5))
        if random.random() < 0.1:
            raise Exception("Gateway connection error")

    async def send_webhook_notification(self, payment: PaymentEntity) -> None:
        """
        Production-level logic for sending async webhook notification.
        """
        payload = {
            "payment_id": str(payment.id),
            "status": payment.status.value,
            "idempotency_key": payment.idempotency_key,
        }
        try:
            await self._webhook_client.send_notification(
                url=payment.webhook_url, payload=payload
            )
        except Exception as exc:
            logger.error(
                "Failed to send webhook for payment %s to %s: %s",
                payment.id,
                payment.webhook_url,
                exc,
            )
