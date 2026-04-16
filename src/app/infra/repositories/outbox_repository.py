"""
SQLAlchemy implementation of AbstractOutboxRepository.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.app_layer.interfaces.repositories import AbstractOutboxRepository
from app.infra.db.models import OutboxORM


class SqlAlchemyOutboxRepository(AbstractOutboxRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event_type: str, payload: dict) -> None:
        row = OutboxORM(event_type=event_type, payload=payload)
        self._session.add(row)

    async def get_unpublished(self, limit: int = 100) -> list[dict]:
        stmt = (
            select(OutboxORM)
            .where(OutboxORM.published == False)  # noqa: E712
            .limit(limit)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [{"id": r.id, "event_type": r.event_type, "payload": r.payload} for r in rows]

    async def mark_published(self, event_id: uuid.UUID) -> None:
        row = await self._session.get(OutboxORM, event_id)
        if row:
            row.published = True
            row.published_at = datetime.utcnow()
