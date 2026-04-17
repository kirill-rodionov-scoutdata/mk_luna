import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.models.payment import Currency, PaymentStatus


class PaymentCreateDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    idempotency_key: str
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict
    webhook_url: str


class PaymentOutputDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: uuid.UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
