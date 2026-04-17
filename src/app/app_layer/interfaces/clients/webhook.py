from abc import ABC, abstractmethod


class AbstractWebhookClient(ABC):
    @abstractmethod
    async def send_notification(self, url: str, payload: dict) -> None:
        """Send an asynchronous webhook notification."""
        ...
