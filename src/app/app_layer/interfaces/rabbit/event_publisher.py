"""
Abstract event publisher interface.

Decouples the app_layer from RabbitMQ / FastStream.
The infra layer provides the concrete implementation.
"""

from abc import ABC, abstractmethod


class AbstractEventPublisher(ABC):
    """Publishes domain events to the message broker."""

    @abstractmethod
    async def publish(self, routing_key: str, payload: dict) -> None:
        """
        Publish an event.

        :param routing_key: RabbitMQ routing key (e.g. "payments.new")
        :param payload: JSON-serialisable dict
        """
        ...
