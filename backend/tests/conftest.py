import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import (
    get_db,
    get_indexing_runner,
    get_ingestion_runner,
    get_preparation_runner,
    get_rate_limit_backend,
    get_request_chat_provider,
    get_request_embedding_provider,
)
from app.core.config import settings
from app.core.rate_limit import InMemoryRateLimitBackend
from app.observability.logging import configure_logging
from app.documents.preparation import prepare_document
from app.embeddings.indexing import index_document
from app.main import app
from app.models.base import Base
from app.ingestion.pipeline import ingest_document
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
from app.models.types import Vector
from app.models.usage import OrganizationUsageDay


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embedding(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._embedding(query)

    @staticmethod
    def _embedding(text: str) -> list[float]:
        normalized = text.lower()
        embedding = [0.0] * settings.embedding_dimensions
        embedding[0] = 1.0 if "refund" in normalized else 0.0
        embedding[1] = 1.0 if "shipping" in normalized else 0.0
        embedding[2] = 1.0 if "password" in normalized else 0.0
        if not any(embedding[:3]):
            embedding[3] = 1.0
        return embedding


class FakeChatProvider:
    def generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        assert "Use only the context" in system_prompt
        assert "[source 1]" in user_prompt
        return "Customers can request a refund within 14 days of purchase."


# Importing the app configures INFO-level JSON logging, which turns a test
# run into thousands of request lines. The formatter is tested directly in
# test_observability.py; here it only needs to be out of the way.
configure_logging(level="WARNING", as_json=False)


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@compiles(Vector, "sqlite")
def compile_vector_for_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, _record):
    """SQLite ignores foreign keys unless asked not to.

    Deletion relies on `ON DELETE CASCADE` doing the work, and without this
    pragma SQLite silently leaves the children behind — so the tests would
    pass while asserting nothing about the behaviour Postgres will actually
    have.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
test_tables = [
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


@pytest.fixture
def session_factory():
    """The test session factory, for code that opens its own sessions.

    Exposed as a fixture rather than imported directly: pytest loads this file
    as `conftest`, so `from tests.conftest import ...` would load it a second
    time under a different module name, producing a second engine and a second
    in-memory database that has none of the tables.
    """
    return TestingSessionLocal


@pytest.fixture
def db() -> Session:
    Base.metadata.create_all(bind=engine, tables=test_tables)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine, tables=reversed(test_tables))


@pytest.fixture(autouse=True)
def temporary_upload_directory(tmp_path):
    original_upload_dir = settings.upload_dir
    original_storage_backend = settings.storage_backend
    original_max_size = settings.max_upload_size_mb
    original_auto_ingest = settings.auto_ingest_on_upload
    original_chunk_size = settings.chunk_size
    original_chunk_overlap = settings.chunk_overlap
    original_embedding_dimensions = settings.embedding_dimensions
    original_index_batch_size = settings.index_batch_size
    original_rag_top_k = settings.rag_top_k
    original_rag_max_context_chars = settings.rag_max_context_chars
    original_rate_limit_enabled = settings.rate_limit_enabled
    original_auth_max = settings.rate_limit_auth_max_requests
    original_chat_max = settings.rate_limit_chat_max_requests
    original_budget_enabled = settings.daily_budget_enabled
    original_budget = settings.daily_token_budget
    # Same reasoning as the rate limits: the check stays on so it is genuinely
    # exercised, with the ceiling lifted out of every other test's way.
    settings.daily_token_budget = 100_000_000
    # Limiting stays on so the dependency is genuinely exercised, but the
    # ceilings are lifted out of the way. A test that cares about the limit
    # lowers them itself; every other test would otherwise be one refactor
    # away from failing for a reason that has nothing to do with it.
    settings.rate_limit_auth_max_requests = 1000
    settings.rate_limit_chat_max_requests = 1000
    settings.upload_dir = tmp_path / "uploads"
    settings.storage_backend = "local"
    settings.max_upload_size_mb = 10
    settings.auto_ingest_on_upload = False
    settings.chunk_size = 1200
    settings.chunk_overlap = 200
    settings.embedding_dimensions = 1536
    settings.index_batch_size = 50
    settings.rag_top_k = 5
    settings.rag_max_context_chars = 12000
    try:
        yield
    finally:
        settings.upload_dir = original_upload_dir
        settings.storage_backend = original_storage_backend
        settings.max_upload_size_mb = original_max_size
        settings.auto_ingest_on_upload = original_auto_ingest
        settings.chunk_size = original_chunk_size
        settings.chunk_overlap = original_chunk_overlap
        settings.embedding_dimensions = original_embedding_dimensions
        settings.index_batch_size = original_index_batch_size
        settings.rag_top_k = original_rag_top_k
        settings.rag_max_context_chars = original_rag_max_context_chars
        settings.rate_limit_enabled = original_rate_limit_enabled
        settings.rate_limit_auth_max_requests = original_auth_max
        settings.rate_limit_chat_max_requests = original_chat_max
        settings.daily_budget_enabled = original_budget_enabled
        settings.daily_token_budget = original_budget


@pytest.fixture
def rate_limit_backend() -> InMemoryRateLimitBackend:
    """A counter that starts empty for every test.

    Sharing one backend across tests would make each test's result depend on
    how many requests the tests before it happened to send.
    """
    return InMemoryRateLimitBackend()


@pytest.fixture
def client(db: Session, rate_limit_backend: InMemoryRateLimitBackend) -> TestClient:
    def override_get_db():
        yield db

    # The trailing session_factory is ignored: these always run against the
    # in-memory test session. It exists so prepare_document can call them with
    # the same signature it uses for the real runners.
    def run_ingestion_for_test(
        document_id, organization_id, force=False, _factory=None, raise_on_error=False
    ):
        ingest_document(
            document_id,
            organization_id,
            force,
            session_factory=TestingSessionLocal,
            raise_on_error=raise_on_error,
        )

    def get_fake_embedding_provider():
        return FakeEmbeddingProvider()

    def run_indexing_for_test(
        document_id, organization_id, force=False, _factory=None, raise_on_error=False
    ):
        index_document(
            document_id,
            organization_id,
            force,
            session_factory=TestingSessionLocal,
            provider_factory=get_fake_embedding_provider,
            raise_on_error=raise_on_error,
        )

    def run_preparation_for_test(
        document_id, organization_id, force=False, raise_on_error=False
    ):
        prepare_document(
            document_id,
            organization_id,
            force,
            session_factory=TestingSessionLocal,
            ingest=run_ingestion_for_test,
            index=run_indexing_for_test,
            raise_on_error=raise_on_error,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ingestion_runner] = lambda: run_ingestion_for_test
    app.dependency_overrides[get_indexing_runner] = lambda: run_indexing_for_test
    app.dependency_overrides[get_preparation_runner] = lambda: run_preparation_for_test
    app.dependency_overrides[get_request_embedding_provider] = (
        get_fake_embedding_provider
    )
    app.dependency_overrides[get_request_chat_provider] = FakeChatProvider
    app.dependency_overrides[get_rate_limit_backend] = lambda: rate_limit_backend
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
