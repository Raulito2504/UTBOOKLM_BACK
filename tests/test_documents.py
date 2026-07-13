import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.v1.dependencies import get_current_user
from src.models import DocumentStatus, JobStatus
from src.modules.documents import repository, router, service
from src.modules.documents.storage import validate_upload_file
from src.modules.rag_chat.chunking import TextChunk


def document_factory(**overrides):
    data = {
        "id": uuid4(),
        "organization_id": uuid4(),
        "uploaded_by_user_id": uuid4(),
        "title": "notes",
        "file_path": "storage/documents/notes.pdf",
        "original_filename": "notes.pdf",
        "mime_type": "application/pdf",
        "storage_backend": "local",
        "file_size_bytes": 128,
        "page_count": 0,
        "status": DocumentStatus.PROCESSING,
        "created_at": datetime.now(UTC),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def job_factory(document_id, **overrides):
    data = {
        "id": uuid4(),
        "document_id": document_id,
        "status": JobStatus.PENDING,
        "error_message": None,
        "created_at": datetime.now(UTC),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_documents_endpoints_require_auth() -> None:
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(SimpleNamespace(), None))

    assert exc.value.status_code == 401


def test_upload_endpoint_returns_processing_document(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), organization_id=uuid4(), is_active=True)
    document = document_factory(organization_id=user.organization_id)
    job = job_factory(document.id)

    async def upload_document(db, *, current_user, file):
        return document, job

    monkeypatch.setattr(service, "upload_document", upload_document)
    file = SimpleNamespace(filename="notes.pdf", content_type="application/pdf")

    response = asyncio.run(
        router.upload(SimpleNamespace(), user, file),
    )

    assert response.document.status == DocumentStatus.PROCESSING
    assert response.ingestion_job.document_id == document.id


def test_list_endpoint_paginates_by_organization(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), organization_id=uuid4(), is_active=True)
    document = document_factory(organization_id=user.organization_id)

    async def list_documents_by_organization(db, *, organization_id, limit, offset):
        assert organization_id == user.organization_id
        assert limit == 1
        assert offset == 2
        return [document]

    async def count_documents_by_organization(db, *, organization_id):
        assert organization_id == user.organization_id
        return 3

    monkeypatch.setattr(
        repository,
        "list_documents_by_organization",
        list_documents_by_organization,
    )
    monkeypatch.setattr(
        repository,
        "count_documents_by_organization",
        count_documents_by_organization,
    )
    response = asyncio.run(
        router.list_documents(
            SimpleNamespace(),
            user,
            {"limit": 1, "offset": 2},
        ),
    )

    assert response.total == 3
    assert response.items[0].id == document.id


def test_detail_endpoint_hides_other_organization_document(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), organization_id=uuid4(), is_active=True)

    async def get_document_or_none(db, *, document_id, organization_id):
        return None

    monkeypatch.setattr(service, "get_document_or_none", get_document_or_none)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(router.get_document(SimpleNamespace(), user, uuid4()))

    assert exc.value.status_code == 404


def test_status_endpoint_returns_latest_job(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), organization_id=uuid4(), is_active=True)
    document = document_factory(organization_id=user.organization_id)
    job = job_factory(document.id, status=JobStatus.COMPLETED)

    async def get_document_or_none(db, *, document_id, organization_id):
        return document

    async def get_latest_ingestion_job(db, *, document_id):
        return job

    monkeypatch.setattr(service, "get_document_or_none", get_document_or_none)
    monkeypatch.setattr(repository, "get_latest_ingestion_job", get_latest_ingestion_job)

    response = asyncio.run(
        router.get_document_status(SimpleNamespace(), user, document.id),
    )

    assert response.ingestion_job.status == JobStatus.COMPLETED


def test_delete_endpoint_calls_service(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), organization_id=uuid4(), is_active=True)
    document = document_factory(organization_id=user.organization_id)
    deleted = []

    async def get_document_or_none(db, *, document_id, organization_id):
        return document

    async def delete_document_with_assets(db, *, document):
        deleted.append(document.id)

    monkeypatch.setattr(service, "get_document_or_none", get_document_or_none)
    monkeypatch.setattr(
        service,
        "delete_document_with_assets",
        delete_document_with_assets,
    )

    response = asyncio.run(router.delete_document(SimpleNamespace(), user, document.id))

    assert response is None
    assert deleted == [document.id]


def test_upload_validation_rejects_large_file(monkeypatch) -> None:
    file = SimpleNamespace(filename="notes.pdf", content_type="application/pdf")

    with pytest.raises(ValueError):
        validate_upload_file(file, 51 * 1024 * 1024)


def test_process_document_job_marks_ready(monkeypatch) -> None:
    document = document_factory()
    job = job_factory(document.id)
    chunks_created = []
    statuses = []

    async def get_document(db, *, document_id):
        return document

    async def get_latest_ingestion_job(db, *, document_id):
        return job

    async def update_ingestion_job_status(db, *, job, status, error_message=None):
        job.status = status
        job.error_message = error_message
        return job

    async def delete_document_chunks(db, *, document_id):
        return None

    async def create_document_chunk(db, **kwargs):
        chunks_created.append(kwargs)
        return SimpleNamespace(**kwargs)

    async def update_document_page_count(db, *, document, page_count):
        document.page_count = page_count
        return document

    async def update_document_status(db, *, document, status):
        statuses.append(status)
        document.status = status
        return document

    monkeypatch.setattr(repository, "get_document", get_document)
    monkeypatch.setattr(repository, "get_latest_ingestion_job", get_latest_ingestion_job)
    monkeypatch.setattr(
        repository,
        "update_ingestion_job_status",
        update_ingestion_job_status,
    )
    monkeypatch.setattr(repository, "delete_document_chunks", delete_document_chunks)
    monkeypatch.setattr(repository, "create_document_chunk", create_document_chunk)
    monkeypatch.setattr(repository, "update_document_page_count", update_document_page_count)
    monkeypatch.setattr(repository, "update_document_status", update_document_status)
    monkeypatch.setattr(
        service,
        "parse_document_text",
        lambda file_path: ([TextChunk(index=0, content="hello", page_number=1)], 1),
    )
    monkeypatch.setattr(service, "index_document_chunks", lambda document, chunks: [])

    db = SimpleNamespace(commit=lambda: None)

    async def commit():
        return None

    db.commit = commit
    result = asyncio.run(service.process_document_job(db, document_id=document.id))

    assert result.status == DocumentStatus.READY
    assert chunks_created[0]["content"] == "hello"
    assert statuses[-1] == DocumentStatus.READY


def test_process_document_job_marks_failed(monkeypatch) -> None:
    document = document_factory()
    job = job_factory(document.id)

    async def get_document(db, *, document_id):
        return document

    async def get_latest_ingestion_job(db, *, document_id):
        return job

    async def update_ingestion_job_status(db, *, job, status, error_message=None):
        job.status = status
        job.error_message = error_message
        return job

    async def update_document_status(db, *, document, status):
        document.status = status
        return document

    monkeypatch.setattr(repository, "get_document", get_document)
    monkeypatch.setattr(repository, "get_latest_ingestion_job", get_latest_ingestion_job)
    monkeypatch.setattr(
        repository,
        "update_ingestion_job_status",
        update_ingestion_job_status,
    )
    monkeypatch.setattr(repository, "update_document_status", update_document_status)

    def parse_document_text(file_path):
        raise RuntimeError("parser failed")

    monkeypatch.setattr(service, "parse_document_text", parse_document_text)

    async def commit():
        return None

    db = SimpleNamespace(commit=commit)
    result = asyncio.run(service.process_document_job(db, document_id=document.id))

    assert result.status == DocumentStatus.FAILED
    assert job.status == JobStatus.FAILED
    assert job.error_message == "parser failed"
