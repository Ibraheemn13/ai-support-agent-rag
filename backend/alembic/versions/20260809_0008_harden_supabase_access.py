"""harden Supabase API access and complete tenant RLS

Supabase exposes the public schema through its Data API and grants its API
roles table access by default. SupportMind uses FastAPI as the only public
data boundary, so those roles must not be able to query these tables around
the application. This matters most for identity and membership tables, which
are intentionally readable by the backend before an organization scope is
known and therefore do not use tenant RLS.

This revision also adds the tenant policy omitted from message_feedback.

Revision ID: 20260809_0008
Revises: 20260808_0007
Create Date: 2026-08-09
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260809_0008"
down_revision: str | None = "20260808_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


POLICY_NAME = "tenant_isolation"
PREDICATE = (
    "organization_id = "
    "nullif(current_setting('app.current_organization_id', true), '')::uuid"
)
ADDITIONAL_TENANT_TABLES = ("message_feedback",)
APPLICATION_TABLES = (
    "users",
    "organizations",
    "organization_members",
    "knowledge_bases",
    "documents",
    "document_chunks",
    "conversations",
    "messages",
    "message_citations",
    "message_feedback",
    "organization_usage_days",
)
SUPABASE_API_ROLES = ("anon", "authenticated", "service_role")


def _revoke_api_role(role: str) -> None:
    tables = ", ".join(APPLICATION_TABLES)
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                REVOKE ALL PRIVILEGES ON TABLE {tables} FROM {role};
                REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public
                    FROM {role};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    REVOKE ALL PRIVILEGES ON TABLES FROM {role};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    REVOKE ALL PRIVILEGES ON SEQUENCES FROM {role};
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    for table in ADDITIONAL_TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {POLICY_NAME} ON {table} "
            f"USING ({PREDICATE}) WITH CHECK ({PREDICATE})"
        )

    tables = ", ".join(APPLICATION_TABLES)
    op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {tables} FROM PUBLIC")
    for role in SUPABASE_API_ROLES:
        _revoke_api_role(role)


def downgrade() -> None:
    for table in ADDITIONAL_TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Privileges stay revoked. Re-granting Data API access on downgrade would
    # create a security exposure that did not necessarily exist beforehand.
