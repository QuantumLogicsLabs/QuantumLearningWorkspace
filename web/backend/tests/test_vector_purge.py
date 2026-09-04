import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import Response
from bson import ObjectId
from fastapi.testclient import TestClient

from main import app
from auth_utils import get_current_user_email

client = TestClient(app)

TEST_USER_EMAIL = "testuser@example.com"


def override_get_current_user_email():
    return TEST_USER_EMAIL


@pytest.fixture(autouse=True)
def override_auth_dependency():
    app.dependency_overrides[get_current_user_email] = override_get_current_user_email
    yield
    app.dependency_overrides.pop(get_current_user_email, None)



@pytest.mark.asyncio
async def test_delete_upload_triggers_vector_purge_and_deletes_record():
    fake_upload_id = str(ObjectId())
    fake_doc_id = "doc-uuid-12345"
    fake_upload_doc = {
        "_id": ObjectId(fake_upload_id),
        "user_id": TEST_USER_EMAIL,
        "document_id": fake_doc_id,
        "filename": "sample.pdf",
    }

    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=fake_upload_doc)
    mock_collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

    with patch("main.get_uploads_collection", return_value=mock_collection), \
         patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_delete_http, \
         patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_os_remove:

        mock_delete_http.return_value = Response(200, json={"status": "purged"})

        response = client.delete(f"/uploads/{fake_upload_id}")

        assert response.status_code == 200
        assert response.json() == {
            "message": "Upload and vector embeddings deleted successfully"
        }

        # Verify Vector purge API was called with the document_id and user_id param
        mock_delete_http.assert_called_once()
        called_url = mock_delete_http.call_args[0][0]
        called_params = mock_delete_http.call_args[1].get("params")

        assert f"/documents/{fake_doc_id}" in called_url
        assert called_params == {"user_id": TEST_USER_EMAIL}

        # Verify local file removal and MongoDB deletion were executed
        mock_os_remove.assert_called()
        mock_collection.delete_one.assert_called_once()


@pytest.mark.asyncio
async def test_delete_upload_returns_404_when_not_found():
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=None)

    with patch("main.get_uploads_collection", return_value=mock_collection):
        fake_id = str(ObjectId())
        response = client.delete(f"/uploads/{fake_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Upload not found"