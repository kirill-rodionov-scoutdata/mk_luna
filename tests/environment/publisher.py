"""
Fake publisher for tests that must not touch RabbitMQ.
"""


class FakePublisher:
    def __init__(self) -> None:
        self.published: list[dict] = []

    async def publish(self, routing_key: str, payload: dict) -> None:
        self.published.append({"routing_key": routing_key, "payload": payload})
