import asyncio
import logging
import uuid

from dependency_injector.wiring import Provide, inject
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue
from tenacity import retry, stop_after_attempt, wait_fixed

from app.app_layer.interfaces.outbox_messages.service import AbstractOutboxService
from app.config import settings
from app.container import Container

logger = logging.getLogger(__name__)

# DLQ Configuration
dlq_exchange = RabbitExchange(settings.rabbitmq.dlx_name, type=ExchangeType.DIRECT)
dlq_queue = RabbitQueue(settings.rabbitmq.payments_dlq_name)

payments_queue = RabbitQueue(
    settings.rabbitmq.payments_queue_name,
    arguments={
        "x-dead-letter-exchange": dlq_exchange.name,
    },
)

broker = RabbitBroker(settings.rabbitmq.url)


@broker.subscriber(payments_queue)
@retry(
    stop=stop_after_attempt(settings.rabbitmq.payments_retry_count),
    wait=wait_fixed(0.1),
    reraise=True,
)
@inject
async def handle_payment_created(
    payment_id: str,
    outbox_service: AbstractOutboxService = Provide[Container.outbox_service],
) -> None:
    logger.info("Received payment event: %s", payment_id)
    payment_id_uuid = uuid.UUID(payment_id)
    await outbox_service.process_payment(payment_id_uuid)


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
