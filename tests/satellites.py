from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

from app.app_layer.interfaces.unit_of_work.sql import AbstractUnitOfWork
from app.app_layer.services.outbox import OutboxService
from app.app_layer.services.payment import PaymentService
from app.domain.models.payment import Currency, PaymentEntity


def make_payment_entity(record: dict[str, Any]) -> PaymentEntity:
    return PaymentEntity(
        amount=Decimal(str(record["amount"])),
        currency=Currency(record["currency"]),
        description=record["description"],
        metadata=record.get("metadata", {}),
        idempotency_key=record["idempotency_key"],
        webhook_url=record["webhook_url"],
    )


def make_payment_api_body(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "amount": str(record["amount"]),
        "currency": record["currency"],
        "description": record["description"],
        "metadata": record.get("metadata", {}),
        "webhook_url": record["webhook_url"],
    }


def make_payment_service(uow: AbstractUnitOfWork) -> PaymentService:
    return PaymentService(uow=uow, on_outbox_write=lambda: None)


def make_outbox_service(uow: AbstractUnitOfWork) -> OutboxService:
    return OutboxService(uow=uow, webhook_client=AsyncMock())
