"""Row-level security, against a real Postgres.

The rest of the suite runs on in-memory SQLite, which has no row-level
security and no session variables — it would report these policies as working
without ever evaluating one. So this module talks to Postgres or skips.

Set `RLS_TEST_DATABASE_URL` to run it:

    RLS_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/rls_test

CI sets it against a pgvector service. Locally it is opt-in, so nobody has to
have Postgres up to run the other 80-odd tests.

Two connections, deliberately. The owner builds the schema, creates the
application role and installs the policies; the application role is what the
assertions run as. Testing through the owner would have proved nothing — the
first version of this file did exactly that and passed while the policies were
being bypassed, because Postgres exempts superusers and table owners from
row-level security.
"""

import importlib.util
import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.tenancy import (
    organization_scope,
    warn_if_row_level_security_is_bypassed,
)
from app.models.base import Base
from app.models.conversation import (
    Conversation,
    Message,
    MessageCitation,
    MessageFeedback,
)
from app.models.document import Document, DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.models.usage import OrganizationUsageDay


DATABASE_URL = os.environ.get("RLS_TEST_DATABASE_URL")


def _migration(filename: str, module_name: str):
    """The RLS migration, loaded by path.

    Alembic revisions are not importable as modules — the directory is not a
    package and the filenames start with a digit. Loading it anyway is worth
    the four lines: the policy SQL asserted here is then literally the SQL
    that ships, not a copy of it that can quietly drift.
    """
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / filename
    )
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_RLS_MIGRATION = _migration(
    "20260806_0005_enable_row_level_security.py",
    "rls_migration",
)
_USAGE_MIGRATION = _migration(
    "20260808_0007_add_organization_usage_days.py",
    "usage_migration",
)
_HARDENING_MIGRATION = _migration(
    "20260809_0008_harden_supabase_access.py",
    "hardening_migration",
)
TENANT_TABLES = (
    *_RLS_MIGRATION.TENANT_TABLES,
    *_USAGE_MIGRATION.TENANT_TABLES,
    *_HARDENING_MIGRATION.ADDITIONAL_TENANT_TABLES,
)
POLICY_NAME = _RLS_MIGRATION.POLICY_NAME
PREDICATE = _RLS_MIGRATION.PREDICATE

if not DATABASE_URL and os.environ.get("REQUIRE_RLS_TESTS"):
    # CI sets this. A skipped security test is indistinguishable from a passing
    # one in a job summary, so where these are supposed to run, not running
    # them is a failure rather than a quiet omission.
    raise RuntimeError(
        "REQUIRE_RLS_TESTS is set but RLS_TEST_DATABASE_URL is not; "
        "row-level security would go untested"
    )

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="RLS_TEST_DATABASE_URL is not set; row-level security needs Postgres",
)

TABLES = [
    User.__table__,
    Organization.__table__,
    OrganizationMember.__table__,
    KnowledgeBase.__table__,
    Document.__table__,
    DocumentChunk.__table__,
    Conversation.__table__,
    Message.__table__,
    MessageCitation.__table__,
    MessageFeedback.__table__,
    OrganizationUsageDay.__table__,
]


ROLE = settings.app_db_role
ROLE_PASSWORD = settings.app_db_password


def _application_url() -> str:
    """The same database, reached as the non-owning application role."""
    url = make_url(DATABASE_URL)
    return url.set(username=ROLE, password=ROLE_PASSWORD).render_as_string(
        hide_password=False
    )


@pytest.fixture(scope="module")
def owner_engine():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(bind=engine, tables=list(reversed(TABLES)))
    Base.metadata.create_all(bind=engine, tables=TABLES)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}'
                    ) THEN
                        CREATE ROLE {ROLE} LOGIN NOSUPERUSER NOBYPASSRLS
                            PASSWORD '{ROLE_PASSWORD}';
                    ELSE
                        ALTER ROLE {ROLE} NOSUPERUSER NOBYPASSRLS
                            PASSWORD '{ROLE_PASSWORD}';
                    END IF;
                END
                $$;
                """
            )
        )
        connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {ROLE}"))
        connection.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                f"IN SCHEMA public TO {ROLE}"
            )
        )
        # The same DDL the migration applies, imported rather than retyped so
        # the test cannot drift into proving a policy that is not the shipped
        # one.
        for table in TENANT_TABLES:
            connection.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            connection.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
            connection.execute(
                text(
                    f"CREATE POLICY {POLICY_NAME} ON {table} "
                    f"USING ({PREDICATE}) WITH CHECK ({PREDICATE})"
                )
            )
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine, tables=list(reversed(TABLES)))
        engine.dispose()


@pytest.fixture(scope="module")
def engine(owner_engine):
    """The connection the application would use: owns nothing, bypasses nothing."""
    engine = create_engine(_application_url())
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _organization(session_factory, name: str) -> uuid.UUID:
    """Create an organization. Not a tenant table, so no scope is needed."""
    db = session_factory()
    try:
        organization = Organization(name=name, slug=f"{name}-{uuid.uuid4().hex[:8]}")
        db.add(organization)
        db.commit()
        return organization.id
    finally:
        db.close()


def _knowledge_base(session_factory, organization_id: uuid.UUID, name: str) -> uuid.UUID:
    with organization_scope(str(organization_id)):
        db = session_factory()
        try:
            knowledge_base = KnowledgeBase(
                organization_id=organization_id,
                name=name,
            )
            db.add(knowledge_base)
            db.commit()
            return knowledge_base.id
        finally:
            db.close()


@pytest.fixture
def two_tenants(session_factory):
    first = _organization(session_factory, "first")
    second = _organization(session_factory, "second")
    _knowledge_base(session_factory, first, "First handbook")
    _knowledge_base(session_factory, second, "Second handbook")
    try:
        yield first, second
    finally:
        for organization_id in (first, second):
            with organization_scope(str(organization_id)):
                db = session_factory()
                try:
                    db.query(KnowledgeBase).delete()
                    db.commit()
                finally:
                    db.close()
        db = session_factory()
        try:
            db.query(Organization).delete()
            db.commit()
        finally:
            db.close()


def test_an_unfiltered_query_returns_only_the_scoped_tenant(
    session_factory, two_tenants
):
    first, _second = two_tenants

    with organization_scope(str(first)):
        db = session_factory()
        try:
            # Deliberately missing the organization filter — this is the bug
            # the policy exists to contain.
            names = db.scalars(select(KnowledgeBase.name)).all()
        finally:
            db.close()

    assert names == ["First handbook"]


def test_a_query_with_no_scope_returns_nothing(session_factory, two_tenants):
    db = session_factory()
    try:
        names = db.scalars(select(KnowledgeBase.name)).all()
    finally:
        db.close()

    # Failing closed: a missing scope is a bug, and an empty result is a bug
    # someone notices immediately.
    assert names == []


def test_another_tenants_row_is_invisible_even_by_id(session_factory, two_tenants):
    first, second = two_tenants
    with organization_scope(str(second)):
        db = session_factory()
        try:
            target = db.scalars(select(KnowledgeBase)).one()
            target_id = target.id
        finally:
            db.close()

    with organization_scope(str(first)):
        db = session_factory()
        try:
            assert db.get(KnowledgeBase, target_id) is None
        finally:
            db.close()


def test_writing_into_another_tenant_is_refused(session_factory, two_tenants):
    first, second = two_tenants

    with organization_scope(str(first)):
        db = session_factory()
        try:
            db.add(KnowledgeBase(organization_id=second, name="Smuggled"))
            with pytest.raises(DBAPIError):
                db.commit()
        finally:
            db.rollback()
            db.close()


def test_the_scope_survives_a_commit(session_factory, two_tenants):
    """The pooled-connection trap.

    A session hands its connection back on commit, so the setting applied when
    the session opened is gone by the next statement. The scope is reapplied on
    every transaction rather than once per session, and this is what checks it.
    """
    first, _second = two_tenants

    with organization_scope(str(first)):
        db = session_factory()
        try:
            assert len(db.scalars(select(KnowledgeBase)).all()) == 1
            db.commit()
            assert len(db.scalars(select(KnowledgeBase)).all()) == 1
        finally:
            db.close()


def test_identity_tables_stay_readable_without_a_scope(session_factory, two_tenants):
    """Organizations are how a request works out its scope in the first place."""
    db = session_factory()
    try:
        assert len(db.scalars(select(Organization)).all()) == 2
    finally:
        db.close()


def test_an_unfiltered_delete_only_reaches_the_scoped_tenant(
    session_factory, two_tenants
):
    """The policy applies to writes too, which is what makes deletion safe.

    A `DELETE` with no organization filter is the same class of bug as a
    `SELECT` with none, and considerably worse. Under the policy it removes
    the scoped tenant's rows and leaves everyone else's.
    """
    first, second = two_tenants

    with organization_scope(str(first)):
        db = session_factory()
        try:
            db.query(KnowledgeBase).delete()
            db.commit()
        finally:
            db.close()

    with organization_scope(str(second)):
        db = session_factory()
        try:
            assert db.scalars(select(KnowledgeBase.name)).all() == ["Second handbook"]
        finally:
            db.close()


def test_the_startup_check_tells_the_two_roles_apart(engine, owner_engine):
    """The check that would have caught the mistake this file was built around."""
    assert warn_if_row_level_security_is_bypassed(engine) is True
    assert warn_if_row_level_security_is_bypassed(owner_engine) is False


def test_every_tenant_table_has_the_policy_forced(engine):
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT relname FROM pg_class "
                "WHERE relrowsecurity AND relforcerowsecurity "
                "AND relname = ANY(:names)"
            ),
            {"names": list(TENANT_TABLES)},
        ).scalars()
        forced = set(rows)

    # FORCE keeps the protection meaningful even if ownership changes during
    # maintenance; the normal application role is deliberately non-owning.
    assert forced == set(TENANT_TABLES)
