"""
Request / Response Pydantic schemas for the payments API.

Deliberately separate from domain models:
  - Request schemas validate & parse incoming JSON
  - Response schemas control what the API exposes (never leak internal fields)
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from app.domain.models.payment import Currency, PaymentStatus


# ── Request schemas ───────────────────────────────────────────────────────────

class CreatePaymentRequest(BaseModel):
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: HttpUrl


# ── Response schemas ──────────────────────────────────────────────────────────

class PaymentCreatedResponse(BaseModel):
    payment_id: uuid.UUID
    status: PaymentStatus
    created_at: datetime


class PaymentDetailResponse(BaseModel):
    payment_id: uuid.UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
