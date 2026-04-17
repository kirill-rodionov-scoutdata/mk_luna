"""
Reset the payments database to a clean state.

Drops all application tables, PostgreSQL enums, and the alembic_version
table so that `alembic upgrade head` can be re-applied from scratch.

Usage (from project root):
    POSTGRES_HOST=localhost uv run python scripts/reset_db.py
"""

import asyncio
import sys
import pathlib

# Ensure src/ is on the path so app.config resolves correctly
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


INDEXES = [
    "ix_outbox_published",
    "ix_payments_idempotency_key",
]

TABLES = [
    "outbox_messages",
    "payments",
    "alembic_version",
]

ENUMS = [
    "payment_status_enum",
    "currency_enum",
]


async def reset() -> None:
    print(f"Connecting to: {settings.database_url!r}")
    engine = create_async_engine(settings.database_url, echo=True)

    async with engine.begin() as conn:
        # Drop indexes first (IF EXISTS is safe when table is already gone)
        for index in INDEXES:
            await conn.execute(
                text(f"DROP INDEX IF EXISTS {index}")
            )
            print(f"  ✓ Dropped index: {index}")

        # Drop tables
        for table in TABLES:
            await conn.execute(
                text(f"DROP TABLE IF EXISTS {table} CASCADE")
            )
            print(f"  ✓ Dropped table: {table}")

        # Drop enums
        for enum in ENUMS:
            await conn.execute(
                text(f"DROP TYPE IF EXISTS {enum} CASCADE")
            )
            print(f"  ✓ Dropped type:  {enum}")

    await engine.dispose()
    print("\nDatabase reset complete. Run `make migrate` to re-apply migrations.")


if __name__ == "__main__":
    asyncio.run(reset())
