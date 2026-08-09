import uuid
from collections.abc import Sequence
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import resolve_storage_path
from app.documents.cleanup import remove_files
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.document import DocumentPage, DocumentResponse
from app.schemas.pagination import decode_cursor, encode_cursor


SUPPORTED_FILE_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "text/plain": {".txt"},
    "text/markdown": {".md", ".markdown"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
}
UPLOAD_CHUNK_SIZE = 1024 * 1024


class DocumentNotFoundError(Exception):
    pass


class KnowledgeBaseNotFoundError(Exception):
    pass


class UnsupportedDocumentTypeError(Exception):
    pass


class InvalidUploadError(Exception):
    pass


class UploadTooLargeError(Exception):
    pass


class DocumentStorageError(Exception):
    pass


class DocumentFileUnavailableError(Exception):
    """The row exists but its bytes do not.

    Distinct from `DocumentNotFoundError` because the two need different
    answers: one means "no such document", the other means "this document is
    real, and the file behind it is gone". Uploads currently live on the
    container filesystem, so every file disappears on a restart — the caller
    has to be able to say that rather than claim the document never existed.
    """


class DocumentBusyError(Exception):
    """A worker may be part-way through this document right now.

    Deleting it would not stop the work — the embedding calls are already in
    flight and already billable — so the honest answer is to refuse and say
    why, rather than accept a delete that silently fails to cancel anything.
    A stale claim is released by the sweep, so the wait is bounded.
    """


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.knowledge_bases = KnowledgeBaseRepository(db)

    async def upload(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        file: UploadFile,
        title: str | None,
    ) -> Document:
        if self.knowledge_bases.get_by_id(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        ) is None:
            raise KnowledgeBaseNotFoundError

        original_name, extension, mime_type = self._validate_file(file)
        document_title = self._normalize_title(title, original_name)
        stored_name = f"{uuid.uuid4().hex}{extension}"
        upload_root = Path(settings.upload_dir)
        configured_path = (
            upload_root
            / str(organization_id)
            / str(knowledge_base_id)
            / stored_name
        )
        stored_path = resolve_storage_path(configured_path)

        try:
            stored_path.parent.mkdir(parents=True, exist_ok=True)
            await self._write_file(file, stored_path)
        except (InvalidUploadError, UploadTooLargeError):
            stored_path.unlink(missing_ok=True)
            raise
        except OSError as exc:
            stored_path.unlink(missing_ok=True)
            raise DocumentStorageError from exc
        finally:
            await file.close()

        try:
            document = self.documents.create_upload(
                organization_id=organization_id,
                knowledge_base_id=knowledge_base_id,
                title=document_title,
                file_name=original_name,
                file_path=configured_path.as_posix(),
                mime_type=mime_type,
            )
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            stored_path.unlink(missing_ok=True)
            raise
        self.db.refresh(document)
        return document

    def list_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
    ) -> list[Document]:
        return self.documents.list_for_organization(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        )

    def list_page(
        self,
        *,
        organization_id: uuid.UUID,
        limit: int,
        knowledge_base_id: uuid.UUID | None = None,
        search: str | None = None,
        statuses: Sequence[str] | None = None,
        cursor: str | None = None,
    ) -> DocumentPage:
        after = decode_cursor(cursor) if cursor else None
        documents, has_more = self.documents.list_page(
            organization_id=organization_id,
            limit=limit,
            knowledge_base_id=knowledge_base_id,
            search=search,
            statuses=statuses,
            after=after,
        )
        last = documents[-1] if documents else None
        return DocumentPage(
            items=[DocumentResponse.model_validate(row) for row in documents],
            next_cursor=(
                encode_cursor(last.created_at, last.id)
                if last is not None and has_more
                else None
            ),
            has_more=has_more,
            status_counts=self.documents.status_counts(
                organization_id=organization_id,
                knowledge_base_id=knowledge_base_id,
                search=search,
            ),
        )

    def get(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document:
        document = self.documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if document is None:
            raise DocumentNotFoundError
        return document

    def open_file(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> tuple[Document, Path]:
        """Locate the stored upload behind a document, for serving back.

        The path is read from the database and then checked to be inside the
        upload root before it is opened. That check is not defending against
        today's writer — `upload` builds the path itself from generated UUIDs —
        but against this column ever carrying a value it did not write. A
        filesystem read assembled from a database string is exactly the shape
        of a path traversal, and the containment check costs one comparison.
        """
        document = self.get(
            organization_id=organization_id,
            document_id=document_id,
        )
        if not document.file_path:
            raise DocumentFileUnavailableError

        upload_root = resolve_storage_path(settings.upload_dir)
        stored_path = resolve_storage_path(document.file_path)
        if not stored_path.is_relative_to(upload_root):
            raise DocumentFileUnavailableError
        if not stored_path.is_file():
            raise DocumentFileUnavailableError

        return document, stored_path

    def delete(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> None:
        document = self.documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if document is None:
            raise DocumentNotFoundError
        if document.status == "processing":
            raise DocumentBusyError

        file_path = document.file_path
        self.documents.delete(document)
        self.db.commit()
        # After the commit, deliberately. See app/documents/cleanup.py.
        remove_files([file_path] if file_path else [])

    @staticmethod
    def _validate_file(file: UploadFile) -> tuple[str, str, str]:
        original_name = Path(file.filename or "").name
        if not original_name or len(original_name) > 255:
            raise InvalidUploadError

        mime_type = file.content_type or ""
        allowed_extensions = SUPPORTED_FILE_EXTENSIONS.get(mime_type)
        extension = Path(original_name).suffix.lower()
        if allowed_extensions is None or extension not in allowed_extensions:
            raise UnsupportedDocumentTypeError
        return original_name, extension, mime_type

    @staticmethod
    def _normalize_title(title: str | None, original_name: str) -> str:
        normalized = title.strip() if title is not None else Path(original_name).stem.strip()
        if not normalized or len(normalized) > 255:
            raise InvalidUploadError
        return normalized

    @staticmethod
    async def _write_file(file: UploadFile, stored_path: Path) -> None:
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        bytes_written = 0
        with stored_path.open("xb") as destination:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise UploadTooLargeError
                destination.write(chunk)
        if bytes_written == 0:
            raise InvalidUploadError
