from pathlib import Path
from tempfile import NamedTemporaryFile
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Document, DocumentChunk, DocumentStatus, User
from src.modules.dashboard import service as dashboard_service
from src.modules.documents import repository
from src.modules.documents.storage import DocumentStorage, validate_upload_file
from src.modules.rag_chat.chunking import TextChunk, chunk_text


class DocumentNotFoundError(Exception):
    pass


class EmptyDocumentError(Exception):
    pass


class UnsupportedDocumentError(Exception):
    pass


class DocumentParseError(Exception):
    pass


async def upload_document(
    db: AsyncSession,
    *,
    current_user: User,
    filename: str,
    content_type: str | None,
    content: bytes,
    title: str | None = None,
    storage: DocumentStorage,
) -> Document:
    if not content:
        raise EmptyDocumentError

    upload_file = _UploadFileStub(filename=filename, content_type=content_type)
    try:
        validate_upload_file(upload_file, len(content))
    except ValueError as exc:
        raise UnsupportedDocumentError(str(exc)) from exc

    parse_path = _write_temp_document(content, filename)
    try:
        chunks, page_count = parse_document_text(parse_path)
    except ValueError as exc:
        raise UnsupportedDocumentError(str(exc)) from exc
    except RuntimeError as exc:
        raise DocumentParseError(str(exc)) from exc
    finally:
        Path(parse_path).unlink(missing_ok=True)

    file_path = storage.save(content, filename)

    try:
        document = await repository.create_document(
            db,
            organization_id=current_user.organization_id,
            uploaded_by_user_id=current_user.id,
            title=(title or Path(filename).stem or "Untitled document").strip(),
            file_path=file_path,
            file_size_bytes=len(content),
            page_count=page_count,
            original_filename=filename,
            mime_type=content_type,
            storage_backend=storage.backend,
            status=DocumentStatus.READY,
        )
        for chunk in chunks:
            await repository.create_document_chunk(
                db,
                document_id=document.id,
                chunk_index=chunk.index,
                content=chunk.content,
                page_number=chunk.page_number,
            )
        await dashboard_service.record_activity(
            db,
            current_user=current_user,
            activity_type="document_uploaded",
            metadata_json={
                "document_id": str(document.id),
                "title": document.title,
                "chunk_count": len(chunks),
            },
        )
    except Exception:
        storage.delete(file_path)
        raise
    return document


async def list_documents(
    db: AsyncSession,
    *,
    current_user: User,
    limit: int = 20,
    offset: int = 0,
) -> list[Document]:
    return await repository.list_documents_by_organization(
        db,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )


async def get_document(
    db: AsyncSession,
    *,
    current_user: User,
    document_id: uuid.UUID,
) -> Document:
    document = await repository.get_document_by_organization(
        db,
        document_id=document_id,
        organization_id=current_user.organization_id,
    )
    if document is None:
        raise DocumentNotFoundError
    return document


async def list_chunks(
    db: AsyncSession,
    *,
    current_user: User,
    document_id: uuid.UUID,
) -> list[DocumentChunk]:
    document = await get_document(db, current_user=current_user, document_id=document_id)
    return await repository.list_document_chunks(db, document_id=document.id)


async def delete_document(
    db: AsyncSession,
    *,
    current_user: User,
    document_id: uuid.UUID,
    storage: DocumentStorage,
) -> None:
    document = await get_document(db, current_user=current_user, document_id=document_id)
    await repository.delete_document(db, document=document)
    storage.delete(document.file_path)


def _write_temp_document(content: bytes, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    with NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
        temp_file.write(content)
        return temp_file.name


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
            page_chunks = chunk_text(page.get_text(), page_number=page_index + 1)
            chunks.extend(
                TextChunk(
                    index=len(chunks) + chunk.index,
                    content=chunk.content,
                    page_number=chunk.page_number,
                )
                for chunk in page_chunks
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


class _UploadFileStub:
    def __init__(self, *, filename: str, content_type: str | None) -> None:
        self.filename = filename
        self.content_type = content_type
