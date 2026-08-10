import uuid
from collections.abc import Callable
from dataclasses import replace
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.ingestion.chunking import TextChunk, chunk_document
from app.ingestion.loaders import (
    ExtractedSection,
    TextExtractionError,
    extract_text_from_file,
)
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.storage import get_storage_provider


logger = logging.getLogger(__name__)


def ingest_document(
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
    force: bool = False,
    session_factory: Callable[[], Session] = SessionLocal,
    raise_on_error: bool = False,
) -> None:
    """Extract text from a stored file and write its chunks.

    `raise_on_error` re-raises after recording the failure on the document.
    The queue needs the exception to decide whether an attempt is worth
    retrying; callers that only care about the recorded status leave it off.
    """
    db = session_factory()
    documents = DocumentRepository(db)
    chunks = DocumentChunkRepository(db)

    try:
        document = documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if document is None:
            return
        if document.status in {"processed", "indexed"} and not force:
            return

        document.status = "processing"
        document.error_message = None
        db.commit()

        if not document.file_path or not document.mime_type:
            raise TextExtractionError("Document has no stored file metadata")

        storage = get_storage_provider()
        # Extractors work with paths. Remote objects are downloaded to a
        # short-lived local file for this job and removed on context exit.
        with storage.materialize(document.file_path) as file_path:
            extracted = extract_text_from_file(str(file_path), document.mime_type)
        extracted_chunks = _chunk_extracted_document(
            extracted.sections,
            source=document.file_path,
        )
        if not extracted_chunks:
            raise TextExtractionError("Document produced no non-empty chunks")

        # Retries replace stale partial chunks; force also reprocesses completed documents.
        chunks.delete_for_document(
            organization_id=organization_id,
            document_id=document_id,
        )
        chunks.create_many(
            organization_id=organization_id,
            document_id=document_id,
            chunks=extracted_chunks,
        )
        document.status = "processed"
        document.error_message = None
        db.commit()
    except Exception as exc:
        logger.exception(
            "Document ingestion failed",
            extra={
                "document_id": str(document_id),
                "organization_id": str(organization_id),
            },
        )
        db.rollback()
        failed_document = documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if failed_document is not None:
            failed_document.status = "failed"
            failed_document.error_message = str(exc)[:4000]
            db.commit()
        if raise_on_error:
            raise
    finally:
        db.close()


def _chunk_extracted_document(
    sections: list[ExtractedSection],
    *,
    source: str,
) -> list[TextChunk]:
    all_chunks: list[TextChunk] = []
    for section in sections:
        section_metadata = {**section.metadata, "source": source}
        section_chunks = chunk_document(
            text=section.text,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            metadata=section_metadata,
        )
        for chunk in section_chunks:
            all_chunks.append(replace(chunk, chunk_index=len(all_chunks)))
    return all_chunks
