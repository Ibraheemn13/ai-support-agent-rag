import uuid

from sqlalchemy.orm import Session

from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.storage import StorageError, get_storage_provider


class IngestionDocumentNotFoundError(Exception):
    pass


class IngestionFileNotFoundError(Exception):
    pass


class IngestionStorageUnavailableError(Exception):
    pass


class DocumentAlreadyIngestedError(Exception):
    pass


class DocumentIngestionInProgressError(Exception):
    pass


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)

    def prepare(
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
            raise IngestionDocumentNotFoundError
        try:
            file_exists = bool(
                document.file_path
                and get_storage_provider().exists(document.file_path)
            )
        except StorageError as exc:
            raise IngestionStorageUnavailableError from exc
        if not file_exists:
            raise IngestionFileNotFoundError
        if document.status == "processing":
            raise DocumentIngestionInProgressError
        if document.status in {"processed", "indexed"} and not force:
            raise DocumentAlreadyIngestedError

        document.status = "processing"
        document.error_message = None
        self.db.commit()
        self.db.refresh(document)
        return document
