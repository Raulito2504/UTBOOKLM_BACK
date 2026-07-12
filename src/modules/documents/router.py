from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from src.api.v1.dependencies import CurrentUser, DatabaseSession, pagination_params
from src.core.exceptions import AppError
from src.modules.documents import service
from src.modules.documents.schemas import DocumentChunkResponse, DocumentResponse
from src.modules.documents.storage import get_document_storage


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"module": "documents", "status": "ready"}


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    db: DatabaseSession,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
) -> DocumentResponse:
    content = await file.read()
    storage = get_document_storage()
    try:
        document = await service.upload_document(
            db,
            current_user=current_user,
            filename=file.filename or "document",
            content_type=file.content_type,
            content=content,
            title=title,
            storage=storage,
        )
        await db.commit()
        await db.refresh(document)
    except service.EmptyDocumentError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="empty_document",
            message="The uploaded document is empty",
        ) from None
    except service.UnsupportedDocumentError as exc:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="unsupported_document",
            message=str(exc) or "Unsupported document",
        ) from None
    except service.DocumentParseError as exc:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="document_parse_failed",
            message=str(exc) or "Could not parse document",
        ) from None

    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
) -> list[DocumentResponse]:
    documents = await service.list_documents(
        db,
        current_user=current_user,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> DocumentResponse:
    try:
        document = await service.get_document(
            db,
            current_user=current_user,
            document_id=document_id,
        )
    except service.DocumentNotFoundError:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="document_not_found",
            message="Document not found",
        ) from None
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkResponse])
async def list_document_chunks(
    document_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[DocumentChunkResponse]:
    try:
        chunks = await service.list_chunks(
            db,
            current_user=current_user,
            document_id=document_id,
        )
    except service.DocumentNotFoundError:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="document_not_found",
            message="Document not found",
        ) from None
    return [DocumentChunkResponse.model_validate(chunk) for chunk in chunks]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    try:
        await service.delete_document(
            db,
            current_user=current_user,
            document_id=document_id,
            storage=get_document_storage(),
        )
        await db.commit()
    except service.DocumentNotFoundError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="document_not_found",
            message="Document not found",
        ) from None
