import uuid

from sqlalchemy.orm import Session

from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.storage import StorageError, get_storage_provider


class PreparationDocumentNotFoundError(Exception):
    pass


class PreparationFileNotFoundError(Exception):
    pass


class PreparationStorageUnavailableError(Exception):
    pass


class DocumentPreparationInProgressError(Exception):
    pass


class DocumentAlreadyPreparedError(Exception):
    pass


class PreparationService:
    """Validates a document before preparation is scheduled.

    Preparation covers both extraction and indexing, so the only states worth
    rejecting are one already running and one already finished.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)

    def start(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        force: bool,
    ) -> Document:
        document = self.documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if document is None:
            raise PreparationDocumentNotFoundError
        try:
            file_exists = bool(
                document.file_path
                and get_storage_provider().exists(document.file_path)
            )
        except StorageError as exc:
            raise PreparationStorageUnavailableError from exc
        if not file_exists:
            raise PreparationFileNotFoundError
        if document.status == "processing":
            raise DocumentPreparationInProgressError
        if document.status == "indexed" and not force:
            raise DocumentAlreadyPreparedError

        # Move to processing straight away when extraction still has to run, so
        # a client polling immediately after the 202 sees progress rather than
        # the pre-request status.
        if force or document.status in {"pending", "failed"}:
            document.status = "processing"
            document.error_message = None
            self.db.commit()
            self.db.refresh(document)

        return document
