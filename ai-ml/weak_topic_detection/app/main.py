"""
Team Lambda Weak Topic Detection API — FastAPI service.

Run from ai-ml/ (so weak_topic_detection.* and quiz_generator.*
imports resolve):
  uvicorn weak_topic_detection.app.main:app --reload --port <TBD — confirm with captain>

Interactive docs (once running): http://127.0.0.1:<port>/docs
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Reusing the JWT auth dependency already built for quiz_generator
# (Contract v1, Section 10) rather than duplicating it — same secret,
# same failure modes, one source of truth for how auth works.
from quiz_generator.app.auth import get_current_user_id

from weak_topic_detection.app.services.weak_topic_service import WeakTopicService

app = FastAPI(title="StudyMind Weak Topic Detection API — Team Lambda")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_service: WeakTopicService | None = None


def get_service() -> WeakTopicService:
    global _service
    if _service is None:
        _service = WeakTopicService()
    return _service


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/weak-topics")
def get_weak_topics_endpoint(user_id: str = Depends(get_current_user_id)):
    """
    Requires "Authorization: Bearer <jwt>". user_id is derived from
    the verified token and returned alongside the results so the
    caller can confirm whose data this is.

    IMPORTANT — current limitation: WeakTopicService reads from a
    static demo dataset (data/quiz_results.json), not live per-user
    quiz submissions. The detection logic itself works correctly, but
    it does not yet filter by user_id — every caller currently sees
    the same demo results. Auth is enforced here so the endpoint's
    contract (who can call it) is correct now; per-user quiz-result
    ingestion is separate follow-up work once real quiz submissions
    are wired in from the frontend.
    """
    service = get_service()
    weak_topics = service.get_weak_topics()

    return {
        "success": True,
        "user_id": user_id,
        "weak_topics": weak_topics,
    }