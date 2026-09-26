"""
Team Lambda Roadmap Generator API — FastAPI service.

Run from ai-ml/ (so roadmap_generator.* and quiz_generator.*
imports resolve):
  uvicorn roadmap_generator.app.main:app --reload --port <TBD — confirm with captain, tentative 8004>

Interactive docs (once running): http://127.0.0.1:<port>/docs

Supports three generation modes via the "mode" field on
POST /generate-roadmap: "topic", "document", "quiz_performance".
See docs/api-contracts.md for the full contract.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

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
    Requires "Authorization: Bearer <jwt>". Dispatches to the correct
    generation path based on body.mode:
      - "topic":            uses body.topic_names / body.priorities
      - "document":         uses body.document_id, scoped to this user
      - "quiz_performance":  uses this user's weak-topic results
    """
    service = get_service()

    try:
        if body.mode == "topic":
            roadmap = service.generate_roadmap(
                topic_names=body.topic_names,
                subject=body.subject,
                step_count=body.step_count,
                priorities=body.priorities,
            )
        elif body.mode == "document":
            roadmap = service.generate_roadmap_from_document(
                user_id=user_id,
                document_id=body.document_id,
                subject=body.subject,
                step_count=body.step_count,
            )
        else:  # "quiz_performance"
            roadmap = service.generate_roadmap_from_quiz_performance(
                user_id=user_id,
                subject=body.subject,
                step_count=body.step_count,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return GenerateRoadmapResponse(
        success=True,
        message=f"Generated {roadmap.total_steps} steps.",
        mode=body.mode,
        subject=roadmap.subject,
        steps=[step.model_dump() for step in roadmap.steps],
        total_steps=roadmap.total_steps,
    )
