import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.app.app_layer.interfaces.outbox_messages.relay import AbstractOutboxRelay
from app.app_layer.interfaces.rabbitmq.event_publisher import AbstractEventPublisher
from app.app_layer.interfaces.repositories import OutboxEventDTO
from app.config import settings
from app.infra.rabbitmq.exceptions import OutboxPersistenceError, OutboxPublishError
from app.infra.unit_of_work.alchemy import UnitOfWork

logger = logging.getLogger(__name__)


class OutboxRelay(AbstractOutboxRelay):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: AbstractEventPublisher,
    ) -> None:
        self.uow = UnitOfWork(session_factory)
        self.publisher = publisher
        self.wakeup = asyncio.Event()
        self._running = True

    def notify(self) -> None:
        self.wakeup.set()

    async def run(self) -> None:
        logger.info(
            "Outbox relay started (poll interval: %ds)",
            settings.outbox.poll_interval_seconds,
        )
        async for _ in self.poll_ticks():
            await self.process_batch()

    def stop(self) -> None:
        self._running = False
        self.wakeup.set()

    async def poll_ticks(self) -> AsyncIterator[None]:
        while self._running:
            try:
                await asyncio.wait_for(
                    self.wakeup.wait(),
                    timeout=settings.outbox.poll_interval_seconds,
                )
            except TimeoutError:
                pass
            self.wakeup.clear()
            yield

    async def process_batch(self) -> None:
        async with self.uow as uow:
            events = await uow.outbox.get_unpublished(limit=100)

        for event in events:
            try:
                await self.publish_event(event)
            except OutboxPublishError as exc:
                logger.warning("%s", exc)
                continue

            try:
                await self.mark_published(event)
            except OutboxPersistenceError as exc:
                # Event reached the broker but DB update failed.
                # It will be republished next cycle (at-least-once delivery).
                logger.warning("%s", exc)

    async def publish_event(self, event: OutboxEventDTO) -> None:
        try:
            await self.publisher.publish(
                routing_key=event.event_type,
                payload=event.payload,
            )
        except Exception as exc:
            raise OutboxPublishError(event.id, event.event_type, exc) from exc

    async def mark_published(self, event: OutboxEventDTO) -> None:
        try:
            async with self.uow as uow:
                await uow.outbox.mark_published(event.id)
        except Exception as exc:
            raise OutboxPersistenceError(event.id, exc) from exc
