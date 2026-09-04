import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient

import database
from main import app
from auth_utils import create_access_token


class MockAsyncCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *args, **kwargs):
        return self

    def __aiter__(self):
        self._iter = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class MockAsyncCollection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        doc_copy = dict(doc)
        if "_id" not in doc_copy:
            doc_copy["_id"] = f"mock-id-{len(self.docs) + 1}"
        self.docs.append(doc_copy)

        class InsertResult:
            inserted_id = doc_copy["_id"]

        return InsertResult()

    async def insert_many(self, docs):
        for d in docs:
            await self.insert_one(d)

    def find(self, query=None):
        query = query or {}
        results = []
        for d in self.docs:
            match = True
            for k, v in query.items():
                if d.get(k) != v:
                    match = False
                    break
            if match:
                results.append(dict(d))
        return MockAsyncCursor(results)


@pytest.fixture(autouse=True)
def mock_collections():
    mock_reviews = MockAsyncCollection()
    mock_cards = MockAsyncCollection()
    with patch.object(database, "get_flashcard_reviews_collection", return_value=mock_reviews), \
         patch.object(database, "get_flashcards_collection", return_value=mock_cards):
        yield {"reviews": mock_reviews, "flashcards": mock_cards}


@pytest.fixture
def auth_headers():
    token = create_access_token("testuser@example.com")
    return {"Authorization": f"Bearer {token}"}


# ==========================================
# 1. Test POST /generate-flashcards
# ==========================================

@pytest.mark.asyncio
async def test_generate_flashcards_default(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/generate-flashcards",
            json={"topic": "Quantum Computing", "num_cards": 4},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["topic"] == "Quantum Computing"
        assert data["total_cards"] == 4
        assert len(data["cards"]) == 4

        # Verify card structure (id, front, back, question, answer, topic)
        for card in data["cards"]:
            assert "id" in card and len(card["id"]) > 0
            assert "front" in card and len(card["front"]) > 0
            assert "back" in card and len(card["back"]) > 0
            assert "question" in card and card["question"] == card["front"]
            assert "answer" in card and card["answer"] == card["back"]
            assert card["topic"] == "Quantum Computing"


@pytest.mark.asyncio
async def test_generate_flashcards_with_content(auth_headers):
    content = "Superposition: A quantum state existing simultaneously.\nEntanglement: Instantaneous correlation between particles."
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/generate-flashcards",
            json={"topic": "Quantum Physics", "num_cards": 2, "content": content},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["cards"]) == 2
        assert "Superposition" in data["cards"][0]["front"] or "Superposition" in data["cards"][0]["back"]


@pytest.mark.asyncio
async def test_generate_flashcards_empty_topic_validation(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/generate-flashcards",
            json={"topic": "   "},
            headers=auth_headers,
        )
        assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_generate_flashcards_card_id_uniqueness(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/generate-flashcards",
            json={"topic": "Machine Learning", "num_cards": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
        cards = response.json()["cards"]
        card_ids = [c["id"] for c in cards]
        assert len(card_ids) == len(set(card_ids)), "All generated card IDs must be unique"


# ==========================================
# 2. Test POST /flashcards/review
# ==========================================

@pytest.mark.asyncio
async def test_review_flashcard_known(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/flashcards/review",
            json={
                "flashcard_id": "card-123",
                "topic": "Python GIL",
                "status": "known",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Review tracked successfully."
        assert data["user_id"] == "testuser@example.com"
        assert data["flashcard_id"] == "card-123"
        assert data["topic"] == "Python GIL"
        assert data["status"] == "known"
        assert data["is_weak"] is False
        assert "date_reviewed" in data


@pytest.mark.asyncio
async def test_review_flashcard_still_learning(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/flashcards/review",
            json={
                "flashcard_id": "card-456",
                "topic": "Quantum Decoherence",
                "status": "still_learning",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "still_learning"
        assert data["is_weak"] is True


@pytest.mark.asyncio
async def test_review_flashcard_invalid_status(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/flashcards/review",
            json={
                "flashcard_id": "card-789",
                "topic": "Algorithms",
                "status": "mastered",  # Invalid status
            },
            headers=auth_headers,
        )
        assert response.status_code == 422


# ==========================================
# 3. Test Weak Topics Detection & Review History
# ==========================================

@pytest.mark.asyncio
async def test_weak_topics_detection(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Topic A: Strong topic (2 known)
        await client.post(
            "/flashcards/review",
            json={"flashcard_id": "c1", "topic": "Calculus", "status": "known"},
            headers=auth_headers,
        )
        await client.post(
            "/flashcards/review",
            json={"flashcard_id": "c2", "topic": "Calculus", "status": "known"},
            headers=auth_headers,
        )

        # Topic B: Weak topic (2 still_learning, 1 known)
        await client.post(
            "/flashcards/review",
            json={"flashcard_id": "c3", "topic": "Quantum Circuits", "status": "still_learning"},
            headers=auth_headers,
        )
        await client.post(
            "/flashcards/review",
            json={"flashcard_id": "c4", "topic": "Quantum Circuits", "status": "still_learning"},
            headers=auth_headers,
        )
        await client.post(
            "/flashcards/review",
            json={"flashcard_id": "c5", "topic": "Quantum Circuits", "status": "known"},
            headers=auth_headers,
        )

        # Query weak-topics endpoint
        response = await client.get("/flashcards/weak-topics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "testuser@example.com"
        assert data["total_reviews"] == 5

        weak_topics = {t["topic"]: t for t in data["weak_topics"]}
        assert "Quantum Circuits" in weak_topics
        assert weak_topics["Quantum Circuits"]["is_weak"] is True
        assert weak_topics["Quantum Circuits"]["still_learning_count"] == 2
        assert weak_topics["Quantum Circuits"]["known_count"] == 1

        assert "Calculus" in weak_topics
        assert weak_topics["Calculus"]["is_weak"] is False
        assert weak_topics["Calculus"]["known_count"] == 2


@pytest.mark.asyncio
async def test_get_user_reviews_history(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/flashcards/review",
            json={"flashcard_id": "card-hist-1", "topic": "Data Science", "status": "known"},
            headers=auth_headers,
        )
        response = await client.get("/flashcards/reviews", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_reviews"] >= 1
        assert any(r["flashcard_id"] == "card-hist-1" for r in data["reviews"])
