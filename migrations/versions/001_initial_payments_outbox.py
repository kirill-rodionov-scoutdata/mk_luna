"""Initial: create payments and outbox tables

Revision ID: 001
Revises:
Create Date: 2026-04-16
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums (raw DDL — avoids SQLAlchemy double-create via _on_table_create) ─
    op.execute("CREATE TYPE currency_enum AS ENUM ('RUB', 'USD', 'EUR')")
    op.execute("CREATE TYPE payment_status_enum AS ENUM ('pending', 'succeeded', 'failed')")

    # ── payments ──────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "currency",
            postgresql.ENUM(name="currency_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="payment_status_enum", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("webhook_url", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_payments_idempotency_key", "payments", ["idempotency_key"])
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"])

    # ── outbox ────────────────────────────────────────────────────────────────
    op.create_table(
        "outbox_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("published", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_published", "outbox_messages", ["published"])


def downgrade() -> None:
    op.drop_index("ix_outbox_published", table_name="outbox_messages")
    op.drop_table("outbox_messages")

    op.drop_index("ix_payments_idempotency_key", table_name="payments")
    op.drop_constraint("uq_payments_idempotency_key", "payments", type_="unique")
    op.drop_table("payments")

    op.execute("DROP TYPE IF EXISTS payment_status_enum")
    op.execute("DROP TYPE IF EXISTS currency_enum")
