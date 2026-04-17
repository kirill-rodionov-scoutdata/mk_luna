from abc import ABC, abstractmethod


class AbstractEventPublisher(ABC):
    @abstractmethod
    async def publish(self, routing_key: str, payload: dict) -> None: ...
