import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    IngestionRunner,
    get_db,
    get_ingestion_runner,
    require_organization_member,
    require_role,
)
from app.core.config import settings
from app.models.document import Document
from app.models.organization import OrganizationMember
from app.schemas.document import DocumentPage, DocumentResponse
from app.schemas.pagination import InvalidCursorError
from app.services.document_service import (
    DocumentBusyError,
    DocumentFileUnavailableError,
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
    InvalidUploadError,
    KnowledgeBaseNotFoundError,
    UnsupportedDocumentTypeError,
    UploadTooLargeError,
)


router = APIRouter(prefix="/organizations/{organization_id}", tags=["documents"])
owner_or_admin = require_role(["owner", "admin"])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    organization_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_or_admin)],
    ingestion_runner: Annotated[IngestionRunner, Depends(get_ingestion_runner)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
) -> Document:
    try:
        document = await DocumentService(db).upload(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            file=file,
            title=title,
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    except UnsupportedDocumentTypeError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported document type",
        )
    except InvalidUploadError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file or title is invalid",
        )
    except UploadTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds the configured size limit",
        )
    except DocumentStorageError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store the uploaded document",
        )
    if settings.auto_ingest_on_upload:
        background_tasks.add_task(
            ingestion_runner,
            document.id,
            organization_id,
            False,
        )
    return document


@router.get("/documents", response_model=DocumentPage)
def list_documents(
    organization_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
    knowledge_base_id: Annotated[uuid.UUID | None, Query()] = None,
    # Searching and filtering happen here rather than in the browser. Client
    # side they only ever worked because the whole collection was already
    # loaded, which is the thing pagination stops being true.
    q: Annotated[str | None, Query(max_length=255)] = None,
    status_filter: Annotated[
        list[str] | None,
        Query(
            alias="status",
            description="Repeatable. Raw document statuses; the UI maps its own labels onto these.",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
) -> DocumentPage:
    try:
        return DocumentService(db).list_page(
            organization_id=organization_id,
            limit=limit,
            knowledge_base_id=knowledge_base_id,
            search=q,
            statuses=status_filter,
            cursor=cursor,
        )
    except InvalidCursorError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid pagination cursor",
        )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
) -> Document:
    try:
        return DocumentService(db).get(
            organization_id=organization_id,
            document_id=document_id,
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )


@router.get("/documents/{document_id}/file")
def get_document_file(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
) -> FileResponse:
    """Serve the original upload back, for reading in the browser.

    Any member may read it: the file is already the source of the answers the
    same member can ask for, so withholding it would protect nothing.
    """
    try:
        document, path = DocumentService(db).open_file(
            organization_id=organization_id,
            document_id=document_id,
        )
    # Both failures carry no-store because 404 and 410 are cacheable by
    # default (RFC 9110). Observed: a browser pinned a 410 and went on
    # reporting the file as gone after it had been restored — which is the
    # normal case here, not a corner one, since a re-upload or a move to
    # object storage brings the bytes back under the same document id.
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
            headers={"Cache-Control": "no-store"},
        )
    except DocumentFileUnavailableError:
        # 410 rather than 404: the document is real and still listed, so
        # "not found" would send the reader looking for the wrong problem.
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "The original file for this document is no longer stored. "
                "Its prepared passages are still searchable."
            ),
            headers={"Cache-Control": "no-store"},
        )

    return FileResponse(
        path,
        media_type=document.mime_type or "application/octet-stream",
        filename=document.file_name or f"{document.title}",
        # Inline so the browser renders it instead of downloading it. That
        # means serving bytes a user uploaded, from our own origin, under a
        # type we recorded at upload from the client's own claim — so pin the
        # type down. Without nosniff a .txt full of markup can be sniffed as
        # HTML and run as this origin.
        content_disposition_type="inline",
        headers={
            "X-Content-Type-Options": "nosniff",
            # One tenant's documents, on an endpoint whose only gate is an
            # Authorization header. `FileResponse` sends an etag and a
            # last-modified date and no cache directive, which leaves a browser
            # free to store the bytes and reuse them heuristically — observed
            # doing exactly that, still serving a document whose file had been
            # deleted. `private` keeps it out of any shared cache; `no-store`
            # keeps a tenant's file off disk entirely.
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_or_admin)],
) -> None:
    try:
        DocumentService(db).delete(
            organization_id=organization_id,
            document_id=document_id,
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    except DocumentBusyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This document is being prepared right now. "
                "Wait for it to finish, then delete it."
            ),
        )
