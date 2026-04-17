import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.container import Container
from app.infra.rabbitmq.broker import broker
from app.infra.rabbitmq.outbox_relay import OutboxRelay


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """
    Startup: wire DI container, start RabbitMQ broker, launch outbox relay.
    Shutdown: cancel relay task, close broker connection.
    """
    container = app.state.container
    container.wire(packages=["app.api"])

    await broker.start()

    relay = OutboxRelay(
        session_factory=container.session_factory(),
        publisher=container.event_publisher(),
    )
    # Wire relay.notify into payment_service so each outbox write wakes the relay immediately
    container.payment_service.add_kwargs(on_outbox_write=relay.notify)
    relay_task = asyncio.create_task(relay.run())

    yield

    relay_task.cancel()
    try:
        await relay_task
    except asyncio.CancelledError:
        pass

    await broker.close()


def create_app() -> FastAPI:
    container = Container()

    application = FastAPI(
        title="Payments Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.container = container
    application.include_router(api_router, prefix="/api/v1")

    return application


app = create_app()
