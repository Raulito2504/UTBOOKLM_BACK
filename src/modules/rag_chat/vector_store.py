from src.infrastructure.vectorstore.chroma_client import get_vector_store


def get_document_vector_store():
    return get_vector_store(collection_name="documents")
