import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from dependency_injector import providers
from faststream.rabbit.testing import TestRabbitBroker

from app.container import Container
from app.infra.rabbitmq.consumer import broker, payments_queue


@pytest.fixture
async def consumer_container(
    mock_outbox_service: AsyncMock,
) -> AsyncGenerator[Container, None]:
    container = Container()
    container.outbox_service.override(providers.Object(mock_outbox_service))
    container.wire(modules=["app.infra.rabbitmq.consumer"])
    yield container
    container.unwire()


async def test_consumer_calls_process_payment_with_correct_uuid(
    consumer_container: Container,
    mock_outbox_service: AsyncMock,
    payment_records: list[dict[str, Any]],
) -> None:
    payment_id = str(uuid.uuid4())

    async with TestRabbitBroker(broker) as tb:
        await tb.publish({"payment_id": payment_id}, queue=payments_queue)

    mock_outbox_service.process_payment.assert_called_once_with(uuid.UUID(payment_id))


async def test_consumer_raises_value_error_on_invalid_uuid(
    consumer_container: Container,
    mock_outbox_service: AsyncMock,
) -> None:
    with pytest.raises(ValueError):
        async with TestRabbitBroker(broker) as tb:
            await tb.publish({"payment_id": "not-a-uuid"}, queue=payments_queue)


async def test_consumer_propagates_service_exception(
    consumer_container: Container,
    mock_outbox_service: AsyncMock,
    payment_records: list[dict[str, Any]],
) -> None:
    mock_outbox_service.process_payment.side_effect = Exception("service failure")
    payment_id = str(uuid.uuid4())

    with pytest.raises(Exception, match="service failure"):
        async with TestRabbitBroker(broker) as tb:
            await tb.publish({"payment_id": payment_id}, queue=payments_queue)
