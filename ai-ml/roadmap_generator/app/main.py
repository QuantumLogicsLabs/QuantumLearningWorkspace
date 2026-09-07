"""
Team Lambda Roadmap Generator API — FastAPI service.

Run from ai-ml/ (so roadmap_generator.* and quiz_generator.*
imports resolve):
  uvicorn roadmap_generator.app.main:app --reload --port <TBD — confirm with captain, tentative 8004>

Interactive docs (once running): http://127.0.0.1:<port>/docs
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Reusing the JWT auth dependency already built for quiz_generator
# (Contract v1, Section 10) — same as weak_topic_detection's endpoint.
from quiz_generator.app.auth import get_current_user_id

from roadmap_generator.app.models.api_models import (
    GenerateRoadmapRequest,
    GenerateRoadmapResponse,
)
from roadmap_generator.app.services.roadmap_service import RoadmapService

app = FastAPI(title="StudyMind Roadmap Generator API — Team Lambda")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_service: RoadmapService | None = None


def get_service() -> RoadmapService:
    global _service
    if _service is None:
        _service = RoadmapService()
    return _service


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/generate-roadmap", response_model=GenerateRoadmapResponse)
def generate_roadmap_endpoint(
    body: GenerateRoadmapRequest,
    user_id: str = Depends(get_current_user_id),
) -> GenerateRoadmapResponse:
    """
    Requires "Authorization: Bearer <jwt>".

    user_id is derived from the verified token and required for
    consistency with Contract v1's auth pattern (every Lambda
    endpoint requires auth), but this module is general-purpose and
    doesn't read per-user content — it only uses the topic_names the
    caller supplies. If a future version personalizes roadmaps using
    a user's own ingested content or weak-topic results, user_id is
    already available here to wire that in without another contract
    change.
    """
    service = get_service()

    try:
        roadmap = service.generate_roadmap(
            topic_names=body.topic_names,
            subject=body.subject,
            step_count=body.step_count,
            priorities=body.priorities,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return GenerateRoadmapResponse(
        success=True,
        message=f"Generated {roadmap.total_steps} steps.",
        subject=roadmap.subject,
        steps=[step.model_dump() for step in roadmap.steps],
        total_steps=roadmap.total_steps,
    )