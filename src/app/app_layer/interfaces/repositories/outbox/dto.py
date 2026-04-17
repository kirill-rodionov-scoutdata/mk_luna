import uuid

from pydantic import BaseModel

from app.domain.models.outbox import OutboxEventType


class OutboxEventDTO(BaseModel):
    id: uuid.UUID
    event_type: OutboxEventType
    payload: dict
