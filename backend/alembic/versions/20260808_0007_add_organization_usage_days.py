"""add per-organization daily model usage

Where the spending cap reads from. One row per organization per UTC day,
carrying token counts and an estimated cost, written after each call that
spent anything.

Under row-level security like every other tenant table, so the usage record is
subject to the same isolation as the data it describes.

Revision ID: 20260808_0007
Revises: 20260807_0006
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260808_0007"
down_revision: str | None = "20260807_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


POLICY_NAME = "tenant_isolation"
TENANT_TABLES = ("organization_usage_days",)
PREDICATE = (
    "organization_id = "
    "nullif(current_setting('app.current_organization_id', true), '')::uuid"
)


def upgrade() -> None:
    op.create_table(
        "organization_usage_days",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "organization_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("embedding_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chat_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "estimated_cost_usd",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_organization_usage_days_organization_id",
        "organization_usage_days",
        ["organization_id"],
    )
    # Unique per organization per day, which is what makes the accumulating
    # write an idempotent upsert rather than a read-modify-write race between
    # two concurrent requests.
    op.create_unique_constraint(
        "uq_organization_usage_days_organization_id_usage_date",
        "organization_usage_days",
        ["organization_id", "usage_date"],
    )

    op.execute("ALTER TABLE organization_usage_days ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE organization_usage_days FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {POLICY_NAME} ON organization_usage_days "
        f"USING ({PREDICATE}) WITH CHECK ({PREDICATE})"
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON organization_usage_days")
    op.drop_table("organization_usage_days")
