import os
import io
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from main import app, UPLOAD_DIRECTORY, process_file_ingestion
from models import Upload
from database import get_uploads_collection
from auth_utils import create_access_token


@pytest.fixture(autouse=True)
def cleanup_uploads_dir():
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    yield
    # Clean up test files created in UPLOAD_DIRECTORY
    for fname in os.listdir(UPLOAD_DIRECTORY):
        if fname.startswith("test_") or fname.endswith(".pdf"):
            try:
                os.remove(os.path.join(UPLOAD_DIRECTORY, fname))
            except Exception:
                pass


def test_upload_model_fields():
    """Verify Upload model contains document_id, chunks_stored, last_error, processed_at."""
    now = datetime.now(timezone.utc)
    upload = Upload(
        filename="lecture_notes.pdf",
        user_id="student@example.com",
        document_id="doc-12345",
        chunks_stored=15,
        last_error=None,
        processed_at=now,
    )

    data = upload.model_dump()
    assert data["filename"] == "lecture_notes.pdf"
    assert data["user_id"] == "student@example.com"
    assert data["document_id"] == "doc-12345"
    assert data["chunks_stored"] == 15
    assert data["last_error"] is None
    assert data["processed_at"] == now


def test_upload_saves_as_document_id_pdf():
    """Verify upload saves physical file as <document_id>.pdf to prevent overwrites."""
    client = TestClient(app)
    token = create_access_token("user_storage_test@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = b"%PDF-1.4 test file content for document storage"
    file_payload = ("syllabus.pdf", io.BytesIO(pdf_content), "application/pdf")

    response = client.post("/upload", files={"file": file_payload}, headers=headers)
    assert response.status_code == 200, response.text
    res_data = response.json()

    assert "document_id" in res_data
    doc_id = res_data["document_id"]
    assert doc_id is not None
    assert res_data["filename"] == "syllabus.pdf"

    # Physical file on disk MUST be named <document_id>.pdf
    physical_path = os.path.join(UPLOAD_DIRECTORY, f"{doc_id}.pdf")
    assert os.path.exists(physical_path), f"File {physical_path} was not created"
    with open(physical_path, "rb") as f:
        assert f.read() == pdf_content

    # Original filename should NOT exist on disk to prevent overwrites
    original_path = os.path.join(UPLOAD_DIRECTORY, "syllabus.pdf")
    assert not os.path.exists(original_path)


@pytest.mark.asyncio
async def test_process_file_ingestion_success(monkeypatch):
    """Verify ingestion updates MongoDB with returned document_id, chunks_stored, and processed_at."""
    user_id = "ingest_user@example.com"
    doc_id = "test-doc-uuid-success"
    physical_file = os.path.join(UPLOAD_DIRECTORY, f"{doc_id}.pdf")
    with open(physical_file, "wb") as f:
        f.write(b"%PDF-1.4 sample text content")

    uploads = get_uploads_collection()
    initial_record = {
        "filename": "sample_doc.pdf",
        "document_id": doc_id,
        "user_id": user_id,
        "status": "Processing",
        "chunks_stored": 0,
        "upload_date": datetime.now(timezone.utc),
    }
    insert_res = await uploads.insert_one(initial_record)
    inserted_id = getattr(insert_res, "inserted_id", None)

    # Mock httpx POST to ingestion service
    class MockResponse:
        status_code = 200
        text = '{"document_id": "test-doc-uuid-success", "chunks_stored": 8, "title": "sample_doc.pdf"}'
        def json(self):
            return {"document_id": "test-doc-uuid-success", "chunks_stored": 8, "title": "sample_doc.pdf"}

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            return MockResponse()

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    await process_file_ingestion(
        file_id=inserted_id,
        document_id=doc_id,
        filename="sample_doc.pdf",
        user_id=user_id,
    )

    updated_doc = await uploads.find_one({"document_id": doc_id, "user_id": user_id})
    assert updated_doc is not None
    assert updated_doc["status"] == "Ready"
    assert updated_doc["document_id"] == "test-doc-uuid-success"
    assert updated_doc["chunks_stored"] == 8
    assert updated_doc["processed_at"] is not None
    assert updated_doc.get("last_error") is None


@pytest.mark.asyncio
async def test_process_file_ingestion_failure(monkeypatch):
    """Verify ingestion failure records last_error and sets status=Failed."""
    user_id = "fail_user@example.com"
    doc_id = "test-doc-uuid-fail"
    physical_file = os.path.join(UPLOAD_DIRECTORY, f"{doc_id}.pdf")
    with open(physical_file, "wb") as f:
        f.write(b"%PDF-1.4 bad pdf")

    uploads = get_uploads_collection()
    initial_record = {
        "filename": "bad_doc.pdf",
        "document_id": doc_id,
        "user_id": user_id,
        "status": "Processing",
        "chunks_stored": 0,
        "upload_date": datetime.now(timezone.utc),
    }
    insert_res = await uploads.insert_one(initial_record)
    inserted_id = getattr(insert_res, "inserted_id", None)

    class MockFailResponse:
        status_code = 500
        text = "ChromaDB connection timeout"
        def json(self):
            return {"error": "ChromaDB connection timeout"}

    class MockFailAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            return MockFailResponse()

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", MockFailAsyncClient)

    await process_file_ingestion(
        file_id=inserted_id,
        document_id=doc_id,
        filename="bad_doc.pdf",
        user_id=user_id,
    )

    updated_doc = await uploads.find_one({"document_id": doc_id, "user_id": user_id})
    assert updated_doc is not None
    assert updated_doc["status"] == "Failed"
    assert "Ingestion failed (500)" in updated_doc["last_error"]
    assert updated_doc["processed_at"] is not None


def test_preview_and_delete_with_document_id():
    """Verify preview and delete endpoints resolve physical <document_id>.pdf."""
    client = TestClient(app)
    token = create_access_token("preview_test@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = b"%PDF-1.4 sample file for preview"
    file_payload = ("preview_target.pdf", io.BytesIO(pdf_content), "application/pdf")

    # 1. Upload
    upload_res = client.post("/upload", files={"file": file_payload}, headers=headers)
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document_id"]

    # 2. Get Uploads list
    list_res = client.get("/uploads", headers=headers)
    assert list_res.status_code == 200
    uploads_list = list_res.json()
    item = next((u for u in uploads_list if u.get("document_id") == doc_id), None)
    assert item is not None
    upload_record_id = item["id"]

    # 3. Preview
    preview_res = client.get(f"/uploads/{upload_record_id}/preview", headers=headers)
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["document_id"] == doc_id
    assert preview_data["filename"] == "preview_target.pdf"
    assert preview_data["file_size"] is not None

    # 4. Delete
    delete_res = client.delete(f"/uploads/{upload_record_id}", headers=headers)
    assert delete_res.status_code == 200

    # Confirm physical file deleted
    physical_path = os.path.join(UPLOAD_DIRECTORY, f"{doc_id}.pdf")
    assert not os.path.exists(physical_path)


if __name__ == "__main__":
    import asyncio
    print("--- Running Test 1: test_upload_model_fields ---")
    test_upload_model_fields()
    print("✓ Passed: test_upload_model_fields")

    print("\n--- Running Test 2: test_upload_saves_as_document_id_pdf ---")
    test_upload_saves_as_document_id_pdf()
    print("✓ Passed: test_upload_saves_as_document_id_pdf")

    print("\n--- Running Test 3: test_preview_and_delete_with_document_id ---")
    test_preview_and_delete_with_document_id()
    print("✓ Passed: test_preview_and_delete_with_document_id")

    class MonkeypatchMock:
        def setattr(self, target, name, value):
            setattr(target, name, value)

    mp = MonkeypatchMock()

    print("\n--- Running Test 4: test_process_file_ingestion_success ---")
    asyncio.run(test_process_file_ingestion_success(mp))
    print("✓ Passed: test_process_file_ingestion_success")

    print("\n--- Running Test 5: test_process_file_ingestion_failure ---")
    asyncio.run(test_process_file_ingestion_failure(mp))
    print("✓ Passed: test_process_file_ingestion_failure")

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
