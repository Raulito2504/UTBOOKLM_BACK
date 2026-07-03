from pathlib import Path

from src.modules.rag_chat.chunking import TextChunk, chunk_text


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
