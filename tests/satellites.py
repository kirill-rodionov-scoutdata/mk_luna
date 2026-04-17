from decimal import Decimal

from app.app_layer.services.payment import PaymentService
from app.app_layer.services.outbox import OutboxService
from app.domain.models.payment import Currency, PaymentEntity


def make_payment_entity(record: dict) -> PaymentEntity:
    return PaymentEntity(
        amount=Decimal(str(record["amount"])),
        currency=Currency(record["currency"]),
        description=record["description"],
        metadata=record.get("metadata", {}),
        idempotency_key=record["idempotency_key"],
        webhook_url=record["webhook_url"],
    )


def make_payment_api_body(record: dict) -> dict:
    return {
        "amount": str(record["amount"]),
        "currency": record["currency"],
        "description": record["description"],
        "metadata": record.get("metadata", {}),
        "webhook_url": record["webhook_url"],
    }


def make_payment_service(uow) -> PaymentService:
    return PaymentService(uow=uow, on_outbox_write=lambda: None)


def make_outbox_service(uow) -> OutboxService:
    return OutboxService(uow=uow)
