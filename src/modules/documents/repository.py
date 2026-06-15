import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Document, DocumentChunk, DocumentStatus


async def create_document(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID,
    title: str,
    file_path: str,
    file_size_bytes: int,
    page_count: int,
    status: DocumentStatus = DocumentStatus.PROCESSING,
) -> Document:
    document = Document(
        organization_id=organization_id,
        uploaded_by_user_id=uploaded_by_user_id,
        title=title,
        file_path=file_path,
        file_size_bytes=file_size_bytes,
        page_count=page_count,
        status=status,
    )
    db.add(document)
    await db.flush()
    return document


async def get_document(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()


async def list_documents_by_organization(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.organization_id == organization_id)
        .order_by(Document.created_at.desc()),
    )
    return list(result.scalars().all())


async def create_document_chunk(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    chunk_index: int,
    content: str,
    page_number: int | None = None,
    vector_id: str | None = None,
    tokens: int | None = None,
) -> DocumentChunk:
    chunk = DocumentChunk(
        document_id=document_id,
        chunk_index=chunk_index,
        content=content,
        page_number=page_number,
        vector_id=vector_id,
        tokens=tokens,
    )
    db.add(chunk)
    await db.flush()
    return chunk


async def list_document_chunks(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
) -> list[DocumentChunk]:
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index),
    )
    return list(result.scalars().all())
