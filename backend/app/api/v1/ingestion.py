import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    IngestionRunner,
    get_db,
    get_ingestion_runner,
    require_role,
)
from app.models.organization import OrganizationMember
from app.schemas.document import IngestionScheduledResponse
from app.services.ingestion_service import (
    DocumentAlreadyIngestedError,
    DocumentIngestionInProgressError,
    IngestionDocumentNotFoundError,
    IngestionFileNotFoundError,
    IngestionStorageUnavailableError,
    IngestionService,
)


router = APIRouter(prefix="/organizations/{organization_id}", tags=["ingestion"])
owner_or_admin = require_role(["owner", "admin"])


@router.post(
    "/documents/{document_id}/ingest",
    response_model=IngestionScheduledResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def schedule_document_ingestion(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_or_admin)],
    ingestion_runner: Annotated[IngestionRunner, Depends(get_ingestion_runner)],
    force: Annotated[bool, Query()] = False,
) -> IngestionScheduledResponse:
    try:
        IngestionService(db).prepare(
            organization_id=organization_id,
            document_id=document_id,
            force=force,
        )
    except IngestionDocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    except IngestionFileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document file is missing from storage",
        )
    except IngestionStorageUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is temporarily unavailable",
        )
    except DocumentAlreadyIngestedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already ingested; use force=true to replace its chunks",
        )
    except DocumentIngestionInProgressError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document ingestion is already in progress",
        )

    background_tasks.add_task(
        ingestion_runner,
        document_id,
        organization_id,
        force,
    )
    return IngestionScheduledResponse(document_id=document_id)
