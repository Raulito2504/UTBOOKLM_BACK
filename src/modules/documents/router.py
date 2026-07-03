from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.api.v1.dependencies import CurrentUser, DatabaseSession, pagination_params
from src.models import DocumentStatus
from src.modules.documents import repository, service
from src.modules.documents.schemas import DocumentDetailResponse, DocumentListResponse
from src.modules.documents.schemas import DocumentResponse, DocumentStatusResponse
from src.modules.documents.schemas import DocumentUploadResponse, IngestionJobResponse


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"module": "documents", "status": "ready"}


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload(
    db: DatabaseSession,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
) -> DocumentUploadResponse:
    try:
        document, job = await service.upload_document(
            db,
            current_user=current_user,
            file=file,
        )
    except ValueError as exc:
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        if "large" not in str(exc).lower():
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from None

    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(document),
        ingestion_job=IngestionJobResponse.model_validate(job),
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
) -> DocumentListResponse:
    documents = await repository.list_documents_by_organization(
        db,
        organization_id=current_user.organization_id,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
    total = await repository.count_documents_by_organization(
        db,
        organization_id=current_user.organization_id,
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(document) for document in documents],
        total=total,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    db: DatabaseSession,
    current_user: CurrentUser,
    doc_id: uuid.UUID,
) -> DocumentDetailResponse:
    document = await service.get_document_or_none(
        db,
        document_id=doc_id,
        organization_id=current_user.organization_id,
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    chunks = await repository.list_document_chunks(db, document_id=document.id)
    job = await repository.get_latest_ingestion_job(db, document_id=document.id)
    return DocumentDetailResponse(
        document=DocumentResponse.model_validate(document),
        chunk_count=len(chunks),
        ingestion_job=IngestionJobResponse.model_validate(job) if job else None,
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    db: DatabaseSession,
    current_user: CurrentUser,
    doc_id: uuid.UUID,
) -> None:
    document = await service.get_document_or_none(
        db,
        document_id=doc_id,
        organization_id=current_user.organization_id,
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await service.delete_document_with_assets(db, document=document)


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    db: DatabaseSession,
    current_user: CurrentUser,
    doc_id: uuid.UUID,
) -> DocumentStatusResponse:
    document = await service.get_document_or_none(
        db,
        document_id=doc_id,
        organization_id=current_user.organization_id,
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    job = await repository.get_latest_ingestion_job(db, document_id=document.id)
    return DocumentStatusResponse(
        document_id=document.id,
        status=DocumentStatus(document.status),
        ingestion_job=IngestionJobResponse.model_validate(job) if job else None,
    )
