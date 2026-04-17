import asyncio
import logging
import uuid

from dependency_injector.wiring import Provide, inject
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.app_layer.interfaces.services import AbstractOutboxService
from app.config import settings
from app.container import Container
from app.domain.models.outbox import OutboxEventType

logger = logging.getLogger(__name__)

# DLQ Configuration
dlq_exchange = RabbitExchange("dead-letter-exchange", type=ExchangeType.DIRECT)
dlq_queue = RabbitQueue("payments.new.dlq")

# Main queue with DLQ linkage
payments_queue = RabbitQueue(
    OutboxEventType.PAYMENTS_NEW,
    dead_letter_exchange=dlq_exchange.name,
)

broker = RabbitBroker(settings.rabbitmq_url)


@broker.subscriber(
    payments_queue,
    retry=3,  # Attempt 3 times before sending to DLQ
)
@inject
async def handle_payment_created(
    payload: dict,
    outbox_service: AbstractOutboxService = Provide[Container.outbox_service],
) -> None:
    logger.info("Received payment event: %s", payload)
    payment_id = uuid.UUID(payload["payment_id"])
    await outbox_service.process_payment(payment_id)


async def main() -> None:
    container = Container()
    container.wire(modules=[__name__])

    async with broker:
        await broker.start()
        logger.info("Consumer started, waiting for messages...")
        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
