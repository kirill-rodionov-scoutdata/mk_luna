"""
Domain model for Payment.

This is a pure Pydantic model — no SQLAlchemy, no I/O.
It represents the payment concept as understood by the business domain.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Currency(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Payment(BaseModel):
    """Core domain model. Instantiated by the service layer, persisted via repo."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: PaymentStatus = PaymentStatus.PENDING
    idempotency_key: str
    webhook_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None
