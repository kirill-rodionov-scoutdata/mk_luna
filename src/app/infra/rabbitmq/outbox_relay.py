import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.app_layer.interfaces.rabbitmq.event_publisher import AbstractEventPublisher
from app.app_layer.interfaces.repositories import OutboxEventDTO
from app.config import settings
from app.infra.rabbitmq.exceptions import OutboxPersistenceError, OutboxPublishError
from app.infra.unit_of_work.alchemy import AlchemyUnitOfWork

logger = logging.getLogger(__name__)


class OutboxRelay:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: AbstractEventPublisher,
    ) -> None:
        self.session_factory = session_factory
        self.publisher = publisher
        self.wakeup = asyncio.Event()

    def notify(self) -> None:
        """Wake up the relay immediately after an outbox write."""
        self.wakeup.set()

    async def run(self) -> None:
        """Long-running coroutine — run via asyncio.create_task in lifespan."""
        logger.info(
            "Outbox relay started (poll interval: %ds)",
            settings.outbox_poll_interval_seconds,
        )
        async for _ in self.poll_ticks():
            await self.process_batch()

    async def poll_ticks(self) -> AsyncIterator[None]:
        """Async generator — yields on wakeup signal or timeout, no sleep."""
        while True:
            try:
                await asyncio.wait_for(
                    self.wakeup.wait(),
                    timeout=settings.outbox_poll_interval_seconds,
                )
            except TimeoutError:
                pass
            self.wakeup.clear()
            yield

    async def process_batch(self) -> None:
        """Fetch one batch of unpublished events and attempt to relay each one."""
        async with AlchemyUnitOfWork(self.session_factory) as uow:
            events = await uow.outbox.get_unpublished(limit=100)

        for event in events:
            try:
                await self.publish_event(event)
            except OutboxPublishError as exc:
                logger.warning("%s", exc)
                continue  # leave unpublished; next poll will retry

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
            async with AlchemyUnitOfWork(self.session_factory) as uow:
                await uow.outbox.mark_published(event.id)
        except Exception as exc:
            raise OutboxPersistenceError(event.id, exc) from exc
