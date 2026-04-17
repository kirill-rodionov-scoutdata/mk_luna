import asyncio
import logging

from faststream.rabbit import RabbitBroker

from app.config import settings

logger = logging.getLogger(__name__)

broker = RabbitBroker(settings.rabbitmq_url)


@broker.subscriber("payments.new")
async def handle_payment_created(payload: dict) -> None:
    logger.info("Received payment event: %s", payload)


async def main() -> None:
    async with broker:
        await broker.start()
        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
