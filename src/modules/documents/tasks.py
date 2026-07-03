import asyncio
import uuid

from src.core.celery_app import celery_app
from src.core.database import get_sessionmaker
from src.modules.documents.service import process_document_job


def process_document(document_id: str) -> dict[str, str]:
    async def run() -> None:
        async with get_sessionmaker()() as db:
            await process_document_job(db, document_id=uuid.UUID(document_id))

    asyncio.run(run())
    return {"document_id": document_id, "status": "processed"}


if celery_app is not None:
    process_document = celery_app.task(name="documents.process_document")(process_document)
