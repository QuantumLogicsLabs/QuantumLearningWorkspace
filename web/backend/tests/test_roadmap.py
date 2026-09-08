import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from main import app
from auth_utils import create_access_token
from tests.test_flashcards import MockAsyncCollection, MockAsyncCursor


@pytest.fixture
def auth_headers():
    token = create_access_token("roadmap_tester@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_recommended_next_steps_unauthenticated():
    """Verify endpoint returns top 3 curated steps when unauthenticated."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/roadmap/next-steps")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "next_steps" in data
        assert 2 <= len(data["next_steps"]) <= 3

        # Check required fields on each step
        first_step = data["next_steps"][0]
        assert "step_number" in first_step
        assert "topic" in first_step
        assert "description" in first_step
        assert "priority" in first_step
        assert "action_label" in first_step
        assert "target_tab" in first_step


@pytest.mark.asyncio
async def test_get_recommended_next_steps_authenticated_with_weak_topics(auth_headers):
    """Verify that weak topics from flashcard reviews are prioritized in roadmap steps."""
    mock_reviews = MockAsyncCollection()
    # Add weak topic (still_learning > known)
    await mock_reviews.insert_one({
        "user_id": "roadmap_tester@example.com",
        "topic": "Quantum Teleportation",
        "status": "still_learning",
    })
    await mock_reviews.insert_one({
        "user_id": "roadmap_tester@example.com",
        "topic": "Quantum Teleportation",
        "status": "still_learning",
    })

    with patch("database.get_flashcard_reviews_collection", return_value=mock_reviews):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/roadmap/next-steps", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["user_id"] == "roadmap_tester@example.com"
            assert 2 <= len(data["next_steps"]) <= 3

            # Verify the weak topic is prioritized as Step 1
            step1 = data["next_steps"][0]
            assert "Quantum Teleportation" in step1["topic"]
            assert step1["priority"] == "high"
            assert step1["target_tab"] == "flashcards"
