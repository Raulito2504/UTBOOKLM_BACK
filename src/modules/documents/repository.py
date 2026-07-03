import uuid

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
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


async def count_documents_by_organization(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(func.count(Document.id)).where(
            Document.organization_id == organization_id,
        ),
    )
    return int(result.scalar_one())


async def update_document_status(
    db: AsyncSession,
    *,
    document: Document,
    status: DocumentStatus,
) -> Document:
    document.status = status
    await db.flush()
    return document


async def update_document_page_count(
    db: AsyncSession,
    *,
    document: Document,
    page_count: int,
) -> Document:
    document.page_count = page_count
    await db.flush()
    return document


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


async def delete_document_chunks(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
) -> None:
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id),
    )
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


async def get_latest_ingestion_job(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
) -> IngestionJob | None:
    result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc()),
    )
    return result.scalars().first()


async def update_ingestion_job_status(
    db: AsyncSession,
    *,
    job: IngestionJob,
    status: JobStatus,
    error_message: str | None = None,
) -> IngestionJob:
    job.status = status
    job.error_message = error_message
    if status == JobStatus.PROCESSING:
        job.started_at = datetime.now(UTC)
    if status in {JobStatus.COMPLETED, JobStatus.FAILED}:
        job.finished_at = datetime.now(UTC)
    await db.flush()
    return job


async def delete_document(
    db: AsyncSession,
    *,
    document: Document,
) -> None:
    await db.delete(document)
    await db.flush()
