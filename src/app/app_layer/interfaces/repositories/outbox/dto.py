import uuid

from pydantic import BaseModel


class OutboxEventDTO(BaseModel):
    id: uuid.UUID
    event_type: str
    payload: dict
