from pathlib import Path
from typing import Any

from src.core.config import get_settings


class VectorStoreClient:
    def __init__(self, collection_name: str = "documents") -> None:
        self.collection_name = collection_name
        self._collection: Any | None = None

    def collection(self) -> Any | None:
        if self._collection is not None:
            return self._collection

        try:
            import chromadb
        except ImportError:
            return None

        settings = get_settings()
        Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = client.get_or_create_collection(self.collection_name)
        return self._collection

    def add_texts(
        self,
        *,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]] | None = None,
    ) -> list[str]:
        collection = self.collection()
        if collection is None or not ids:
            return []

        payload: dict[str, Any] = {
            "ids": ids,
            "documents": texts,
            "metadatas": metadatas,
        }
        if embeddings is not None:
            payload["embeddings"] = embeddings
        collection.add(**payload)
        return ids

    def delete(self, ids: list[str]) -> None:
        collection = self.collection()
        if collection is not None and ids:
            collection.delete(ids=ids)


def get_vector_store(collection_name: str = "documents") -> VectorStoreClient:
    return VectorStoreClient(collection_name=collection_name)
