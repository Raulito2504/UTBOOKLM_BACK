import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.models import (
    ChatMessage,
    ChatSession,
    Document,
    DocumentStatus,
    MessageRole,
    User,
)
from src.modules.dashboard import service as dashboard_service
from src.modules.documents import repository as documents_repository
from src.modules.rag_chat import repository
from src.modules.rag_chat.llm_provider import (
    LlmResponse,
    ProviderConfigurationError,
    ProviderRequestError,
    get_embedding_provider,
    get_llm_provider,
)
from src.modules.rag_chat.schemas import RagSourceResponse
from src.modules.rag_chat.vector_store import (
    RagSearchResult,
    VectorStoreUnavailableError,
    get_document_vector_store,
)


class ChatNotFoundError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class DocumentNotReadyError(Exception):
    pass


class DocumentLimitExceededError(Exception):
    pass


class RagDependencyError(Exception):
    pass


class RagContextEmptyError(Exception):
    pass


async def create_chat(
    db: AsyncSession,
    *,
    current_user: User,
    title: str,
    document_ids: list[uuid.UUID],
) -> ChatSession:
    await _validate_documents(
        db,
        current_user=current_user,
        document_ids=document_ids,
    )
    chat = await repository.create_chat_session(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        title=title,
        document_ids=document_ids,
    )
    await dashboard_service.record_activity(
        db,
        current_user=current_user,
        activity_type="chat_created",
        metadata_json={
            "chat_id": str(chat.id),
            "document_ids": [str(document_id) for document_id in document_ids],
        },
    )
    return chat


async def list_chats(
    db: AsyncSession,
    *,
    current_user: User,
    limit: int = 20,
    offset: int = 0,
) -> list[ChatSession]:
    return await repository.list_chat_sessions(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


async def get_chat(
    db: AsyncSession,
    *,
    current_user: User,
    chat_id: uuid.UUID,
) -> ChatSession:
    chat = await repository.get_chat_session(
        db,
        chat_session_id=chat_id,
        organization_id=current_user.organization_id,
    )
    if chat is None or chat.user_id != current_user.id:
        raise ChatNotFoundError
    return chat


async def update_chat(
    db: AsyncSession,
    *,
    current_user: User,
    chat_id: uuid.UUID,
    title: str | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> ChatSession:
    chat = await get_chat(db, current_user=current_user, chat_id=chat_id)
    if document_ids is not None:
        await _validate_documents(
            db,
            current_user=current_user,
            document_ids=document_ids,
        )
    return await repository.update_chat_session(
        db,
        chat_session=chat,
        title=title,
        document_ids=document_ids,
    )


async def delete_chat(
    db: AsyncSession,
    *,
    current_user: User,
    chat_id: uuid.UUID,
) -> None:
    chat = await get_chat(db, current_user=current_user, chat_id=chat_id)
    await repository.delete_chat_session(db, chat_session=chat)


async def list_messages(
    db: AsyncSession,
    *,
    current_user: User,
    chat_id: uuid.UUID,
) -> list[ChatMessage]:
    chat = await get_chat(db, current_user=current_user, chat_id=chat_id)
    return await repository.list_chat_messages(db, chat_session_id=chat.id)


async def list_chat_sources(
    db: AsyncSession,
    *,
    current_user: User,
    chat_id: uuid.UUID,
) -> list[Document]:
    chat = await get_chat(db, current_user=current_user, chat_id=chat_id)
    return await documents_repository.list_documents_by_ids(
        db,
        organization_id=current_user.organization_id,
        document_ids=chat.document_ids or [],
    )


async def remove_chat_source(
    db: AsyncSession,
    *,
    current_user: User,
    chat_id: uuid.UUID,
    document_id: uuid.UUID,
) -> ChatSession:
    chat = await get_chat(db, current_user=current_user, chat_id=chat_id)
    document_ids = [
        current_document_id
        for current_document_id in chat.document_ids or []
        if current_document_id != document_id
    ]
    return await repository.update_chat_session(
        db,
        chat_session=chat,
        document_ids=document_ids,
    )


async def index_document(
    db: AsyncSession,
    *,
    current_user: User,
    document_id: uuid.UUID,
) -> int:
    document = await _get_ready_document(
        db,
        current_user=current_user,
        document_id=document_id,
    )
    chunks = await documents_repository.list_document_chunks(
        db,
        document_id=document.id,
    )
    chunks_to_index = [chunk for chunk in chunks if not chunk.vector_id]
    if not chunks_to_index:
        return 0

    try:
        embeddings = get_embedding_provider().embed(
            [chunk.content for chunk in chunks_to_index],
        )
        vector_ids = get_document_vector_store().index_chunks(
            organization_id=current_user.organization_id,
            chunks=chunks_to_index,
            embeddings=embeddings,
        )
    except (
        ProviderConfigurationError,
        ProviderRequestError,
        VectorStoreUnavailableError,
    ) as exc:
        raise RagDependencyError(str(exc)) from exc

    for chunk, vector_id in zip(chunks_to_index, vector_ids, strict=True):
        await documents_repository.update_document_chunk_vector_id(
            db,
            chunk=chunk,
            vector_id=vector_id,
        )
    return len(chunks_to_index)


async def create_user_message_and_answer(
    db: AsyncSession,
    *,
    current_user: User,
    chat_id: uuid.UUID,
    question: str,
) -> tuple[ChatMessage, ChatMessage, list[RagSourceResponse]]:
    settings = get_settings()
    if len(question) > settings.rag_max_question_chars:
        question = question[: settings.rag_max_question_chars]

    chat = await get_chat(db, current_user=current_user, chat_id=chat_id)
    if not chat.document_ids:
        raise RagContextEmptyError

    await _ensure_chat_documents_indexed(
        db,
        current_user=current_user,
        document_ids=chat.document_ids,
    )

    user_message = await repository.create_chat_message(
        db,
        chat_session_id=chat.id,
        role=MessageRole.USER,
        content=question,
    )
    search_results = _search_context(
        organization_id=current_user.organization_id,
        document_ids=chat.document_ids,
        question=question,
    )
    if not search_results:
        raise RagContextEmptyError

    prompt = _build_prompt(question=question, search_results=search_results)
    try:
        llm_response = get_llm_provider().complete(prompt)
    except (ProviderConfigurationError, ProviderRequestError) as exc:
        raise RagDependencyError(str(exc)) from exc

    source_responses = [_source_response(result) for result in search_results]
    sources_payload = {
        "items": [source.model_dump(mode="json") for source in source_responses],
    }
    assistant_message = await repository.create_chat_message(
        db,
        chat_session_id=chat.id,
        role=MessageRole.ASSISTANT,
        content=llm_response.content,
        sources=sources_payload,
        tokens_used=llm_response.tokens_used,
    )
    await repository.create_rag_query(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        question=question,
        document_id=chat.document_ids[0] if chat.document_ids else None,
        answer=llm_response.content,
        sources=sources_payload,
        tokens_used=llm_response.tokens_used,
    )
    await dashboard_service.record_activity(
        db,
        current_user=current_user,
        activity_type="rag_message_sent",
        metadata_json={
            "chat_id": str(chat.id),
            "user_message_id": str(user_message.id),
            "assistant_message_id": str(assistant_message.id),
            "source_count": len(source_responses),
            "tokens_used": llm_response.tokens_used,
        },
    )
    return user_message, assistant_message, source_responses


def build_answer(question: str, context: list[str]) -> LlmResponse:
    prompt = "\n".join([*context, question])
    return get_llm_provider().complete(prompt)


async def _validate_documents(
    db: AsyncSession,
    *,
    current_user: User,
    document_ids: list[uuid.UUID],
) -> list[Document]:
    settings = get_settings()
    if len(document_ids) > settings.rag_max_chat_documents:
        raise DocumentLimitExceededError

    documents: list[Document] = []
    for document_id in document_ids:
        document = await _get_ready_document(
            db,
            current_user=current_user,
            document_id=document_id,
        )
        documents.append(document)
    return documents


async def _get_ready_document(
    db: AsyncSession,
    *,
    current_user: User,
    document_id: uuid.UUID,
) -> Document:
    document = await documents_repository.get_document_by_organization(
        db,
        document_id=document_id,
        organization_id=current_user.organization_id,
    )
    if document is None:
        raise DocumentNotFoundError
    if document.status != DocumentStatus.READY:
        raise DocumentNotReadyError
    return document


async def _ensure_chat_documents_indexed(
    db: AsyncSession,
    *,
    current_user: User,
    document_ids: list[uuid.UUID],
) -> None:
    for document_id in document_ids:
        await index_document(db, current_user=current_user, document_id=document_id)


def _search_context(
    *,
    organization_id: uuid.UUID,
    document_ids: list[uuid.UUID],
    question: str,
) -> list[RagSearchResult]:
    settings = get_settings()
    try:
        query_embedding = get_embedding_provider().embed([question])[0]
        return get_document_vector_store().search(
            organization_id=organization_id,
            document_ids=document_ids,
            query_embedding=query_embedding,
            top_k=settings.rag_top_k,
        )
    except (
        ProviderConfigurationError,
        ProviderRequestError,
        VectorStoreUnavailableError,
    ) as exc:
        raise RagDependencyError(str(exc)) from exc


def _build_prompt(*, question: str, search_results: list[RagSearchResult]) -> str:
    settings = get_settings()
    context_parts: list[str] = []
    current_length = 0
    for result in search_results:
        source_header = (
            f"[document_id={result.document_id} "
            f"chunk_id={result.chunk_id} page={result.page_number}]"
        )
        text = f"{source_header}\n{result.content}"
        if current_length + len(text) > settings.rag_max_context_chars:
            break
        context_parts.append(text)
        current_length += len(text)

    context = "\n\n---\n\n".join(context_parts)
    return (
        "Eres el asistente de estudio de UTBookLM.\n"
        "Responde solo con la informacion encontrada en el contexto.\n"
        "Si el contexto no contiene la respuesta, di que no tienes suficiente "
        "informacion.\n"
        "No inventes fuentes, paginas ni datos.\n"
        "Usa un tono claro y util para estudiantes.\n\n"
        f"Contexto:\n{context}\n\n"
        f"Pregunta:\n{question}\n\n"
        "Respuesta:"
    )


def _source_response(result: RagSearchResult) -> RagSourceResponse:
    preview = " ".join(result.content.split())[:280]
    return RagSourceResponse(
        document_id=result.document_id,
        chunk_id=result.chunk_id,
        page_number=result.page_number,
        score=result.score,
        preview=preview,
    )
