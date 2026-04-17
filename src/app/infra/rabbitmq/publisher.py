from app.app_layer.interfaces.rabbitmq.event_publisher import AbstractEventPublisher
from app.infra.rabbitmq.broker import broker


class RabbitMQEventPublisher(AbstractEventPublisher):
    async def publish(self, routing_key: str, payload: dict) -> None:
        await broker.publish(payload, routing_key=routing_key)
