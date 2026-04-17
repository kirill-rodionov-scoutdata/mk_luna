from typing import Any


class FakePublisher:
    def __init__(self) -> None:
        self.published_messages: list[dict[str, Any]] = []

    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        self.published_messages.append({"routing_key": routing_key, "payload": payload})
