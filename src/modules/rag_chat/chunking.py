from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    page_number: int | None = None


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1800,
    overlap: int = 200,
    page_number: int | None = None,
) -> list[TextChunk]:
    clean_text = " ".join(text.split())
    if not clean_text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    index = 0
    step = max(chunk_size - overlap, 1)

    while start < len(clean_text):
        content = clean_text[start : start + chunk_size].strip()
        if content:
            chunks.append(
                TextChunk(index=index, content=content, page_number=page_number),
            )
            index += 1
        start += step

    return chunks
