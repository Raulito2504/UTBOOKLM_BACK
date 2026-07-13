import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ChatMessage, ChatSession, MessageRole, RagQuery


async def create_chat_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    title: str,
    document_ids: list[uuid.UUID] | None = None,
) -> ChatSession:
    chat_session = ChatSession(
        user_id=user_id,
        organization_id=organization_id,
        title=title,
        document_ids=document_ids or [],
    )
    db.add(chat_session)
    await db.flush()
    return chat_session


async def get_chat_session(
    db: AsyncSession,
    *,
    chat_session_id: uuid.UUID,
    organization_id: uuid.UUID | None = None,
) -> ChatSession | None:
    statement = select(ChatSession).where(ChatSession.id == chat_session_id)
    if organization_id is not None:
        statement = statement.where(ChatSession.organization_id == organization_id)
    result = await db.execute(
        statement,
    )
    return result.scalar_one_or_none()


async def list_chat_sessions(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[ChatSession]:
    statement = select(ChatSession).where(
        ChatSession.organization_id == organization_id,
    )
    if user_id is not None:
        statement = statement.where(ChatSession.user_id == user_id)
    result = await db.execute(
        statement.order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .offset(offset),
    )
    return list(result.scalars().all())


async def update_chat_session(
    db: AsyncSession,
    *,
    chat_session: ChatSession,
    title: str | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> ChatSession:
    if title is not None:
        chat_session.title = title
    if document_ids is not None:
        chat_session.document_ids = document_ids
    await db.flush()
    return chat_session


async def delete_chat_session(
    db: AsyncSession,
    *,
    chat_session: ChatSession,
) -> None:
    await db.delete(chat_session)
    await db.flush()


async def create_chat_message(
    db: AsyncSession,
    *,
    chat_session_id: uuid.UUID,
    role: MessageRole,
    content: str,
    sources: dict[str, Any] | None = None,
    tokens_used: int | None = None,
) -> ChatMessage:
    message = ChatMessage(
        chat_session_id=chat_session_id,
        role=role,
        content=content,
        sources=sources,
        tokens_used=tokens_used,
    )
    db.add(message)
    await db.flush()
    return message


async def list_chat_messages(
    db: AsyncSession,
    *,
    chat_session_id: uuid.UUID,
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_session_id == chat_session_id)
        .order_by(ChatMessage.created_at),
    )
    return list(result.scalars().all())


async def create_rag_query(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None = None,
    answer: str | None = None,
    sources: dict[str, Any] | None = None,
    tokens_used: int | None = None,
) -> RagQuery:
    query = RagQuery(
        user_id=user_id,
        organization_id=organization_id,
        document_id=document_id,
        question=question,
        answer=answer,
        sources=sources,
        tokens_used=tokens_used,
    )
    db.add(query)
    await db.flush()
    return query
