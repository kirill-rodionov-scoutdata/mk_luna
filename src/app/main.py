import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import settings
from app.container import Container
from app.infra.rabbitmq.broker import broker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = app.state.container
    container.wire(packages=["app.api"])

    await broker.start()

    relay = container.outbox_relay()
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

    @application.middleware("http")
    async def api_key_middleware(request: Request, call_next):
        if request.url.path.startswith("/api/v1"):
            if request.headers.get("X-API-Key") != settings.api.api_key:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key."},
                )
        return await call_next(request)

    application.state.container = container
    application.include_router(api_router, prefix="/api/v1")

    return application


app = create_app()
