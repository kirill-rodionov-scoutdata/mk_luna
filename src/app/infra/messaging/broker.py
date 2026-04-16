"""
FastStream RabbitMQ broker singleton.

Imported by:
  - main.py  → started/stopped in lifespan
  - consumer.py → decorates subscribers
  - publisher.py → used to publish messages

Exchange/queue topology:
  payments_exchange (direct) → payments.new  → DLQ after 3 NACK retries
"""

from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

from app.config import settings

broker = RabbitBroker(settings.rabbitmq_url)

# ── Exchange ──────────────────────────────────────────────────────────────────
payments_exchange = RabbitExchange("payments_exchange", durable=True)

# ── Dead Letter Queue ─────────────────────────────────────────────────────────
payments_dlq = RabbitQueue(
    "payments.dead_letter",
    durable=True,
)

# ── Main queue (binds to exchange, routes failures to DLQ) ────────────────────
payments_new_queue = RabbitQueue(
    "payments.new",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": "payments.dead_letter",
        "x-message-ttl": 30_000,
    },
)
