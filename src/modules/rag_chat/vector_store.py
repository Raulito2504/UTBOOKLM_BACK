import uuid
from dataclasses import dataclass

from src.core.config import get_settings
from src.infrastructure.vectorstore.chroma_client import get_vector_store
from src.models import DocumentChunk


class VectorStoreUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class RagSearchResult:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    page_number: int | None
    content: str
    score: float | None


class DocumentVectorStore:
    def __init__(self, collection_name: str = "documents") -> None:
        settings = get_settings()
        self.provider = settings.vector_store_provider.lower()
        self.client = get_vector_store(collection_name=collection_name)

    def index_chunks(
        self,
        *,
        organization_id: uuid.UUID,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> list[str]:
        if self.provider != "chroma":
            raise VectorStoreUnavailableError("Unsupported vector store provider")
        collection = self.client.collection()
        if collection is None:
            raise VectorStoreUnavailableError("Vector store is unavailable")
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings length mismatch")

        ids = [str(chunk.id) for chunk in chunks]
        try:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=[chunk.content for chunk in chunks],
                metadatas=[
                    {
                        "organization_id": str(organization_id),
                        "document_id": str(chunk.document_id),
                        "chunk_id": str(chunk.id),
                        "page_number": chunk.page_number or 0,
                    }
                    for chunk in chunks
                ],
            )
        except Exception as exc:
            raise VectorStoreUnavailableError(str(exc)) from exc
        return ids

    def search(
        self,
        *,
        organization_id: uuid.UUID,
        document_ids: list[uuid.UUID],
        query_embedding: list[float],
        top_k: int,
    ) -> list[RagSearchResult]:
        if self.provider != "chroma":
            raise VectorStoreUnavailableError("Unsupported vector store provider")
        collection = self.client.collection()
        if collection is None:
            raise VectorStoreUnavailableError("Vector store is unavailable")

        where = _build_where_filter(
            organization_id=organization_id,
            document_ids=document_ids,
        )
        try:
            response = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreUnavailableError(str(exc)) from exc

        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]

        results: list[RagSearchResult] = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] or {}
            page_number = metadata.get("page_number")
            if page_number == 0:
                page_number = None
            distance = distances[index] if index < len(distances) else None
            score = None if distance is None else max(0.0, 1.0 - float(distance))
            results.append(
                RagSearchResult(
                    chunk_id=uuid.UUID(str(metadata.get("chunk_id") or chunk_id)),
                    document_id=uuid.UUID(str(metadata["document_id"])),
                    page_number=page_number,
                    content=documents[index],
                    score=score,
                ),
            )
        return results


def get_document_vector_store() -> DocumentVectorStore:
    return DocumentVectorStore(collection_name="documents")


def _build_where_filter(
    *,
    organization_id: uuid.UUID,
    document_ids: list[uuid.UUID],
) -> dict:
    organization_filter = {"organization_id": str(organization_id)}
    document_values = [str(document_id) for document_id in document_ids]
    if not document_values:
        return organization_filter
    if len(document_values) == 1:
        return {
            "$and": [
                organization_filter,
                {"document_id": document_values[0]},
            ],
        }
    return {
        "$and": [
            organization_filter,
            {"document_id": {"$in": document_values}},
        ],
    }
