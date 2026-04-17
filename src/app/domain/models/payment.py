import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.app_layer.interfaces.payments.schemas import PaymentOutputDTO
    from app.infra.db.models import PaymentORM


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PaymentEntity(BaseModel):
    """Core domain model. Instantiated by the service layer, persisted via repo."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: PaymentStatus = PaymentStatus.PENDING
    idempotency_key: str
    webhook_url: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None

    @classmethod
    def from_orm(cls, row: "PaymentORM") -> "PaymentEntity":

        return cls(
            id=row.id,
            amount=row.amount,
            currency=Currency(row.currency),
            description=row.description,
            metadata=row.metadata_,
            status=PaymentStatus(row.status),
            idempotency_key=row.idempotency_key,
            webhook_url=row.webhook_url,
            created_at=row.created_at,
            processed_at=row.processed_at,
        )

    def to_orm(self) -> "PaymentORM":
        from app.infra.db.models import PaymentORM

        return PaymentORM(
            id=self.id,
            amount=self.amount,
            currency=self.currency.value,
            description=self.description,
            metadata_=self.metadata,
            status=self.status.value,
            idempotency_key=self.idempotency_key,
            webhook_url=self.webhook_url,
            created_at=self.created_at,
            processed_at=self.processed_at,
        )

    def to_dto(self) -> "PaymentOutputDTO":
        from app.app_layer.interfaces.payments.schemas import PaymentOutputDTO

        return PaymentOutputDTO(
            id=self.id,
            amount=self.amount,
            currency=self.currency,
            description=self.description,
            metadata=self.metadata,
            status=self.status,
            idempotency_key=self.idempotency_key,
            webhook_url=self.webhook_url,
            created_at=self.created_at,
            processed_at=self.processed_at,
        )
