"""add refresh tokens

Sessions previously ended hard at the access token's expiry with no way to
continue and no way to revoke early. This adds the table behind rotating
refresh tokens.

The table is not tenant-scoped, so it gets no RLS policy — it is keyed by user,
like `users` itself, and is read before any organization scope exists. It is
added to the Supabase Data API revocation from 20260809_0008 for the same
reason those tables were: FastAPI is the only intended path to this data, and
session records are the last thing that should be reachable around it.

Revision ID: 20260810_0009
Revises: 20260809_0008
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260810_0009"
down_revision: str | None = "20260809_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SUPABASE_API_ROLES = ("anon", "authenticated", "service_role")


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"]
    )
    op.create_index(
        op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"]
    )
    op.create_index(
        op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"]
    )

    # Postgres only. SQLite runs the schema for tests and has no roles.
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("REVOKE ALL PRIVILEGES ON TABLE refresh_tokens FROM PUBLIC")
    for role in SUPABASE_API_ROLES:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    REVOKE ALL PRIVILEGES ON TABLE refresh_tokens FROM {role};
                END IF;
            END
            $$;
            """
        )

    # The application role connects as a non-owner (ADR-038), so its grants are
    # explicit rather than inherited.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'supportmind_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE refresh_tokens
                    TO supportmind_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_refresh_tokens_token_hash"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_family_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
