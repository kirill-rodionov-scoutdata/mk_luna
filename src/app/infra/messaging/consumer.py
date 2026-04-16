"""
RabbitMQ consumer (single worker process).

Responsibilities (to be implemented):
  1. Receive payment IDs from payments.new queue
  2. Emulate payment processing (2-5s delay, 90% success / 10% failure)
  3. Update payment status in DB
  4. Send webhook notification to payment.webhook_url
  5. Retry webhook up to 3 times with exponential back-off
  6. NACK → DLQ after 3 failed processing attempts

Run standalone:
    PYTHONPATH=src python -m app.infra.messaging.consumer
"""

import asyncio
import logging

from faststream.rabbit import RabbitMessage

from app.infra.messaging.broker import broker, payments_new_queue, payments_exchange

logger = logging.getLogger(__name__)


@broker.subscriber(payments_new_queue, payments_exchange)
async def handle_new_payment(message: dict, raw_message: RabbitMessage) -> None:
    """
    Entry point for payment processing.

    message: {"payment_id": "<uuid>"}

    TODO:
      - Retrieve Payment from DB via UoW
      - asyncio.sleep(random 2-5s) to emulate gateway call
      - random.random() < 0.9 → succeeded, else failed
      - uow.payments.update(payment) with new status + processed_at
      - Send webhook POST; retry 3× with 2^n back-off
      - On final failure: NACK (message goes to DLQ automatically)
    """
    payment_id = message.get("payment_id")
    logger.info("Received payment processing request: %s", payment_id)
    # Implementation placeholder
    ...


async def main() -> None:
    """Start the consumer as a standalone async process."""
    async with broker:
        logger.info("Consumer started. Waiting for messages...")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
