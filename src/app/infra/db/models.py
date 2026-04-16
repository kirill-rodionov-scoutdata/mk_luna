"""
SQLAlchemy ORM mapped classes.

These are persistence models — deliberately separate from the Pydantic domain models.
Alembic autogenerates migrations from this module.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.payment import Currency, PaymentStatus
from app.infra.db.base import Base


class PaymentORM(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(Enum(Currency, name="currency_enum"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutboxORM(Base):
    """
    Outbox table for guaranteed event delivery.
    A background relay reads unpublished rows and publishes them to RabbitMQ.
    """

    __tablename__ = "outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    published: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
