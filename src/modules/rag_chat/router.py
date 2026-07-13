from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.api.v1.dependencies import CurrentUser, DatabaseSession, pagination_params
from src.core.exceptions import AppError
from src.modules.rag_chat import service
from src.modules.rag_chat.schemas import (
    ChatCreateRequest,
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatResponse,
    ChatUpdateRequest,
    DocumentIndexResponse,
    RagGenerateResponse,
)


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"module": "rag", "status": "ready"}


@router.post(
    "/chats",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat(
    payload: ChatCreateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ChatResponse:
    try:
        chat = await service.create_chat(
            db,
            current_user=current_user,
            title=payload.title,
            document_ids=payload.document_ids,
        )
        await db.commit()
        await db.refresh(chat)
    except service.DocumentLimitExceededError:
        await db.rollback()
        raise _document_limit_error() from None
    except service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    return ChatResponse.model_validate(chat)


@router.get("/chats", response_model=list[ChatResponse])
async def list_chats(
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
) -> list[ChatResponse]:
    chats = await service.list_chats(
        db,
        current_user=current_user,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
    return [ChatResponse.model_validate(chat) for chat in chats]


@router.get("/chats/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ChatResponse:
    try:
        chat = await service.get_chat(db, current_user=current_user, chat_id=chat_id)
    except service.ChatNotFoundError:
        raise _chat_not_found_error() from None
    return ChatResponse.model_validate(chat)


@router.patch("/chats/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: UUID,
    payload: ChatUpdateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ChatResponse:
    try:
        chat = await service.update_chat(
            db,
            current_user=current_user,
            chat_id=chat_id,
            title=payload.title,
            document_ids=payload.document_ids,
        )
        await db.commit()
        await db.refresh(chat)
    except service.ChatNotFoundError:
        await db.rollback()
        raise _chat_not_found_error() from None
    except service.DocumentLimitExceededError:
        await db.rollback()
        raise _document_limit_error() from None
    except service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    return ChatResponse.model_validate(chat)


@router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    try:
        await service.delete_chat(db, current_user=current_user, chat_id=chat_id)
        await db.commit()
    except service.ChatNotFoundError:
        await db.rollback()
        raise _chat_not_found_error() from None


@router.get("/chats/{chat_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    chat_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[ChatMessageResponse]:
    try:
        messages = await service.list_messages(
            db,
            current_user=current_user,
            chat_id=chat_id,
        )
    except service.ChatNotFoundError:
        raise _chat_not_found_error() from None
    return [ChatMessageResponse.model_validate(message) for message in messages]


@router.post(
    "/chats/{chat_id}/messages",
    response_model=RagGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    chat_id: UUID,
    payload: ChatMessageCreateRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> RagGenerateResponse:
    try:
        user_message, assistant_message, sources = (
            await service.create_user_message_and_answer(
                db,
                current_user=current_user,
                chat_id=chat_id,
                question=payload.content,
            )
        )
        await db.commit()
        await db.refresh(user_message)
        await db.refresh(assistant_message)
    except service.ChatNotFoundError:
        await db.rollback()
        raise _chat_not_found_error() from None
    except service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    except service.RagContextEmptyError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            error_code="rag_context_empty",
            message="No indexed context is available for this chat",
        ) from None
    except service.RagDependencyError as exc:
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


@router.post(
    "/documents/{document_id}/index",
    response_model=DocumentIndexResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def index_document(
    document_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> DocumentIndexResponse:
    try:
        indexed_chunks = await service.index_document(
            db,
            current_user=current_user,
            document_id=document_id,
        )
        await db.commit()
    except service.DocumentNotFoundError:
        await db.rollback()
        raise _document_not_found_error() from None
    except service.DocumentNotReadyError:
        await db.rollback()
        raise _document_not_ready_error() from None
    except service.RagDependencyError as exc:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="dependency_unavailable",
            message=str(exc) or "RAG dependency is unavailable",
        ) from None

    return DocumentIndexResponse(
        document_id=document_id,
        indexed_chunks=indexed_chunks,
        status="indexed",
    )


def _chat_not_found_error() -> AppError:
    return AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="chat_not_found",
        message="Chat not found",
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
        message="Document is not ready for RAG",
    )


def _document_limit_error() -> AppError:
    return AppError(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="document_limit_exceeded",
        message="Too many documents for a single chat",
    )
