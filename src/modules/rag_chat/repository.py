import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ChatMessage, ChatSession, MessageRole


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
) -> ChatSession | None:
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == chat_session_id),
    )
    return result.scalar_one_or_none()


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
