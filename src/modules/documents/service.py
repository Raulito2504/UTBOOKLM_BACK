from pathlib import Path
import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Document, DocumentStatus, IngestionJob, JobStatus, User
from src.modules.documents import repository
from src.modules.documents.storage import get_document_storage, validate_upload_file
from src.modules.rag_chat.llm_provider import get_embedding_provider
from src.modules.rag_chat.chunking import TextChunk, chunk_text
from src.modules.rag_chat.vector_store import get_document_vector_store


def parse_document_text(file_path: str) -> tuple[list[TextChunk], int]:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(file_path)
    if suffix == ".pptx":
        return parse_pptx(file_path)
    raise ValueError("Unsupported document type")


def parse_pdf(file_path: str) -> tuple[list[TextChunk], int]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF parser is not installed") from exc

    chunks: list[TextChunk] = []
    with fitz.open(file_path) as document:
        for page_index, page in enumerate(document):
            for chunk in chunk_text(page.get_text(), page_number=page_index + 1):
                chunks.append(
                    TextChunk(
                        index=len(chunks),
                        content=chunk.content,
                        page_number=chunk.page_number,
                    ),
                )
        return chunks, document.page_count


def parse_pptx(file_path: str) -> tuple[list[TextChunk], int]:
    try:
        from pptx import Presentation
    except ImportError as exc:
        raise RuntimeError("PPTX parser is not installed") from exc

    presentation = Presentation(file_path)
    chunks: list[TextChunk] = []
    for slide_index, slide in enumerate(presentation.slides):
        text_parts: list[str] = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                text_parts.append(shape.text)
        for chunk in chunk_text("\n".join(text_parts), page_number=slide_index + 1):
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    content=chunk.content,
                    page_number=chunk.page_number,
                ),
            )
    return chunks, len(presentation.slides)


async def upload_document(
    db: AsyncSession,
    *,
    current_user: User,
    file: UploadFile,
) -> tuple[Document, IngestionJob]:
    content = await file.read()
    validate_upload_file(file, len(content))

    storage = get_document_storage()
    filename = file.filename or "document"
    file_path = storage.save(content, filename)
    document = await repository.create_document(
        db,
        organization_id=current_user.organization_id,
        uploaded_by_user_id=current_user.id,
        title=Path(filename).stem or filename,
        file_path=file_path,
        original_filename=filename,
        mime_type=file.content_type,
        storage_backend="local",
        file_size_bytes=len(content),
        page_count=0,
        status=DocumentStatus.PROCESSING,
    )
    job = await repository.create_ingestion_job(
        db,
        document_id=document.id,
        original_filename=filename,
        mime_type=file.content_type,
        storage_backend="local",
    )
    await db.commit()
    enqueue_document_processing(document.id)
    return document, job


def enqueue_document_processing(document_id: uuid.UUID) -> None:
    from src.modules.documents.tasks import process_document

    delay = getattr(process_document, "delay", None)
    if delay is None:
        return
    try:
        delay(str(document_id))
    except Exception:
        return


async def process_document_job(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
) -> Document:
    document = await repository.get_document(db, document_id=document_id)
    if document is None:
        raise ValueError("Document not found")

    job = await repository.get_latest_ingestion_job(db, document_id=document.id)
    if job is not None:
        await repository.update_ingestion_job_status(
            db,
            job=job,
            status=JobStatus.PROCESSING,
        )

    try:
        chunks, page_count = parse_document_text(document.file_path)
        await repository.delete_document_chunks(db, document_id=document.id)
        vector_ids = index_document_chunks(document, chunks)
        for chunk in chunks:
            vector_id = vector_ids[chunk.index] if chunk.index < len(vector_ids) else None
            await repository.create_document_chunk(
                db,
                document_id=document.id,
                chunk_index=chunk.index,
                content=chunk.content,
                page_number=chunk.page_number,
                vector_id=vector_id,
                tokens=len(chunk.content.split()),
            )
        await repository.update_document_page_count(
            db,
            document=document,
            page_count=page_count,
        )
        await repository.update_document_status(
            db,
            document=document,
            status=DocumentStatus.READY,
        )
        if job is not None:
            await repository.update_ingestion_job_status(
                db,
                job=job,
                status=JobStatus.COMPLETED,
            )
        await db.commit()
        return document
    except Exception as exc:
        await repository.update_document_status(
            db,
            document=document,
            status=DocumentStatus.FAILED,
        )
        if job is not None:
            await repository.update_ingestion_job_status(
                db,
                job=job,
                status=JobStatus.FAILED,
                error_message=str(exc),
            )
        await db.commit()
        return document


def index_document_chunks(document: Document, chunks: list[TextChunk]) -> list[str | None]:
    if not chunks:
        return []

    vector_store = get_document_vector_store()
    texts = [chunk.content for chunk in chunks]
    ids = [f"{document.id}:{chunk.index}" for chunk in chunks]
    metadatas = [
        {
            "document_id": str(document.id),
            "chunk_index": chunk.index,
            "page_number": chunk.page_number,
        }
        for chunk in chunks
    ]
    try:
        embeddings = get_embedding_provider().embed(texts)
        return vector_store.add_texts(
            ids=ids,
            texts=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
    except Exception:
        return [None for _ in chunks]


async def get_document_or_none(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Document | None:
    return await repository.get_document_by_organization(
        db,
        document_id=document_id,
        organization_id=organization_id,
    )


async def delete_document_with_assets(
    db: AsyncSession,
    *,
    document: Document,
) -> None:
    chunks = await repository.list_document_chunks(db, document_id=document.id)
    vector_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]
    try:
        get_document_vector_store().delete(vector_ids)
    except Exception:
        pass

    storage = get_document_storage()
    storage.delete(document.file_path)
    await repository.delete_document(db, document=document)
    await db.commit()
