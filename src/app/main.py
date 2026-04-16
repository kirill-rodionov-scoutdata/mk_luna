from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.container import Container
from app.infra.messaging.broker import broker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: wire DI container, start RabbitMQ broker.
    Shutdown: close broker connection.
    """
    container = app.state.container
    container.wire(packages=["app.api"])

    await broker.start()
    yield
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
