from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.api.v1.dependencies import CurrentUser, DatabaseSession, pagination_params
from src.core.exceptions import AppError
from src.modules.dashboard import service as dashboard_service
from src.modules.dashboard.schemas import NotebookCardResponse
from src.modules.notebooks.schemas import NotebookSourcesUpdateRequest
from src.modules.rag_chat import service as rag_service
from src.modules.rag_chat.schemas import (
    ChatCreateRequest,
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatResponse,
    ChatUpdateRequest,
    RagGenerateResponse,
)


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"module": "notebooks", "status": "ready"}


@router.get("", response_model=list[NotebookCardResponse])
async def list_notebooks(
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
) -> list[NotebookCardResponse]:
    return await dashboard_service.list_notebooks(
        db,
        current_user=current_user,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    payload: ChatCreateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ChatResponse:
    try:
        notebook = await rag_service.create_chat(
            db,
            current_user=current_user,
            title=payload.title,
            document_ids=payload.document_ids,
        )
        await db.commit()
        await db.refresh(notebook)
    except rag_service.DocumentLimitExceededError:
        await db.rollback()
        raise _document_limit_error() from None
    except rag_service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except rag_service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    return ChatResponse.model_validate(notebook)


@router.get("/{notebook_id}", response_model=ChatResponse)
async def get_notebook(
    notebook_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ChatResponse:
    try:
        notebook = await rag_service.get_chat(
            db,
            current_user=current_user,
            chat_id=notebook_id,
        )
    except rag_service.ChatNotFoundError:
        raise _notebook_not_found_error() from None
    return ChatResponse.model_validate(notebook)


@router.patch("/{notebook_id}", response_model=ChatResponse)
async def update_notebook(
    notebook_id: UUID,
    payload: ChatUpdateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ChatResponse:
    try:
        notebook = await rag_service.update_chat(
            db,
            current_user=current_user,
            chat_id=notebook_id,
            title=payload.title,
            document_ids=payload.document_ids,
        )
        await db.commit()
        await db.refresh(notebook)
    except rag_service.ChatNotFoundError:
        await db.rollback()
        raise _notebook_not_found_error() from None
    except rag_service.DocumentLimitExceededError:
        await db.rollback()
        raise _document_limit_error() from None
    except rag_service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except rag_service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    return ChatResponse.model_validate(notebook)


@router.post("/{notebook_id}/sources", response_model=ChatResponse)
async def add_notebook_sources(
    notebook_id: UUID,
    payload: NotebookSourcesUpdateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ChatResponse:
    try:
        notebook = await rag_service.get_chat(
            db,
            current_user=current_user,
            chat_id=notebook_id,
        )
        current_document_ids = notebook.document_ids or []
        document_ids = list(
            dict.fromkeys([*current_document_ids, *payload.document_ids]),
        )
        notebook = await rag_service.update_chat(
            db,
            current_user=current_user,
            chat_id=notebook_id,
            document_ids=document_ids,
        )
        await db.commit()
        await db.refresh(notebook)
    except rag_service.ChatNotFoundError:
        await db.rollback()
        raise _notebook_not_found_error() from None
    except rag_service.DocumentLimitExceededError:
        await db.rollback()
        raise _document_limit_error() from None
    except rag_service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except rag_service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    return ChatResponse.model_validate(notebook)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(
    notebook_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    try:
        await rag_service.delete_chat(
            db,
            current_user=current_user,
            chat_id=notebook_id,
        )
        await db.commit()
    except rag_service.ChatNotFoundError:
        await db.rollback()
        raise _notebook_not_found_error() from None


@router.get("/{notebook_id}/messages", response_model=list[ChatMessageResponse])
async def list_notebook_messages(
    notebook_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[ChatMessageResponse]:
    try:
        messages = await rag_service.list_messages(
            db,
            current_user=current_user,
            chat_id=notebook_id,
        )
    except rag_service.ChatNotFoundError:
        raise _notebook_not_found_error() from None
    return [ChatMessageResponse.model_validate(message) for message in messages]


@router.post(
    "/{notebook_id}/messages",
    response_model=RagGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notebook_message(
    notebook_id: UUID,
    payload: ChatMessageCreateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> RagGenerateResponse:
    try:
        user_message, assistant_message, sources = (
            await rag_service.create_user_message_and_answer(
                db,
                current_user=current_user,
                chat_id=notebook_id,
                question=payload.content,
            )
        )
        await db.commit()
        await db.refresh(user_message)
        await db.refresh(assistant_message)
    except rag_service.ChatNotFoundError:
        await db.rollback()
        raise _notebook_not_found_error() from None
    except rag_service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except rag_service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    except rag_service.RagContextEmptyError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            error_code="rag_context_empty",
            message="No indexed context is available for this notebook",
        ) from None
    except rag_service.RagDependencyError as exc:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="dependency_unavailable",
            message=str(exc) or "RAG dependency is unavailable",
        ) from None

    return RagGenerateResponse(
        user_message=ChatMessageResponse.model_validate(user_message),
        assistant_message=ChatMessageResponse.model_validate(assistant_message),
        sources=sources,
    )


def _notebook_not_found_error() -> AppError:
    return AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="notebook_not_found",
        message="Notebook not found",
    )


def _document_not_found_error() -> AppError:
    return AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="document_not_found",
        message="Document not found",
    )


def _document_not_ready_error() -> AppError:
    return AppError(
        status_code=status.HTTP_409_CONFLICT,
        error_code="document_not_ready",
        message="Document is not ready for notebooks",
    )


def _document_limit_error() -> AppError:
    return AppError(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="document_limit_exceeded",
        message="Too many documents for a single notebook",
    )
