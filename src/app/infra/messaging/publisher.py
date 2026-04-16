"""
RabbitMQ implementation of AbstractEventPublisher.

Wraps the FastStream broker to provide the interface the app_layer expects.
"""

from app.app_layer.interfaces.event_publisher import AbstractEventPublisher
from app.infra.messaging.broker import broker, payments_exchange


class RabbitMQEventPublisher(AbstractEventPublisher):
    """Publishes domain events to RabbitMQ via FastStream."""

    async def publish(self, routing_key: str, payload: dict) -> None:
        await broker.publish(
            payload,
            routing_key=routing_key,
            exchange=payments_exchange,
        )
