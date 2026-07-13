import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Document, DocumentChunk, DocumentStatus, IngestionJob, JobStatus


async def create_document(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID,
    title: str,
    file_path: str,
    file_size_bytes: int,
    page_count: int,
    original_filename: str | None = None,
    mime_type: str | None = None,
    storage_backend: str = "local",
    status: DocumentStatus = DocumentStatus.PROCESSING,
) -> Document:
    document = Document(
        organization_id=organization_id,
        uploaded_by_user_id=uploaded_by_user_id,
        title=title,
        file_path=file_path,
        original_filename=original_filename,
        mime_type=mime_type,
        storage_backend=storage_backend,
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


async def get_document_by_organization(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        ),
    )
    return result.scalar_one_or_none()


async def list_documents_by_organization(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.organization_id == organization_id)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset),
    )
    return list(result.scalars().all())


async def list_documents_by_ids(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    document_ids: list[uuid.UUID],
) -> list[Document]:
    if not document_ids:
        return []

    result = await db.execute(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.id.in_(document_ids),
        ),
    )
    documents_by_id = {document.id: document for document in result.scalars().all()}
    return [
        documents_by_id[document_id]
        for document_id in document_ids
        if document_id in documents_by_id
    ]


async def update_document_status(
    db: AsyncSession,
    *,
    document: Document,
    status: DocumentStatus,
) -> Document:
    document.status = status
    await db.flush()
    return document


async def update_document(
    db: AsyncSession,
    *,
    document: Document,
    title: str | None = None,
) -> Document:
    if title is not None:
        document.title = title
    await db.flush()
    return document


async def delete_document(db: AsyncSession, *, document: Document) -> None:
    await db.delete(document)
    await db.flush()


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


async def get_next_document_chunk_index(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(func.max(DocumentChunk.chunk_index)).where(
            DocumentChunk.document_id == document_id,
        ),
    )
    current_max = result.scalar_one()
    if current_max is None:
        return 0
    return int(current_max) + 1


async def count_document_chunks(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == document_id,
        ),
    )
    return int(result.scalar_one())


async def list_document_chunks(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    limit: int | None = None,
    offset: int = 0,
) -> list[DocumentChunk]:
    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    if limit is not None:
        statement = statement.limit(limit).offset(offset)
    result = await db.execute(statement)
    return list(result.scalars().all())


async def update_document_chunk_vector_id(
    db: AsyncSession,
    *,
    chunk: DocumentChunk,
    vector_id: str,
) -> DocumentChunk:
    chunk.vector_id = vector_id
    await db.flush()
    return chunk


async def delete_document_chunks(db: AsyncSession, *, document_id: uuid.UUID) -> None:
    chunks = await list_document_chunks(db, document_id=document_id)
    for chunk in chunks:
        await db.delete(chunk)
    await db.flush()


async def create_ingestion_job(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    original_filename: str | None = None,
    mime_type: str | None = None,
    storage_backend: str = "local",
) -> IngestionJob:
    job = IngestionJob(
        document_id=document_id,
        original_filename=original_filename,
        mime_type=mime_type,
        storage_backend=storage_backend,
        status=JobStatus.PENDING,
    )
    db.add(job)
    await db.flush()
    return job


async def list_ingestion_jobs(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
) -> list[IngestionJob]:
    result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc()),
    )
    return list(result.scalars().all())
