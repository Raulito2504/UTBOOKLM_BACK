from src.core.celery_app import celery_app


def process_document(document_id: str) -> dict[str, str]:
    return {"document_id": document_id, "status": "queued"}


if celery_app is not None:
    process_document = celery_app.task(name="documents.process_document")(process_document)
