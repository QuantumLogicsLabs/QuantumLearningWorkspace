"""
Knowledge Graph API — FastAPI service.

Run from ai-ml/ (so the knowledge_graph.* and embedding.* imports resolve):
  uvicorn knowledge_graph.app.api.graph_routes:app --reload --port 8003

Interactive docs: http://127.0.0.1:8003/docs

[Built in from the start, per NV-2] Every endpoint below requires a
valid JWT, reusing quiz_generator.app.auth's existing, working
implementation — the same fix already applied to ingestion. user_id
is never accepted from the client; it comes only from the verified
token's `sub` claim.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from quiz_generator.app.auth import get_current_user_id
from knowledge_graph.app.services.graph_service import GraphService

app = FastAPI(title="StudyMind Knowledge Graph API — Team Lambda")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_service: GraphService | None = None


def get_service() -> GraphService:
    global _service
    if _service is None:
        _service = GraphService()
    return _service


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/graph")
def get_graph_endpoint(user_id: str = Depends(get_current_user_id)) -> dict:
    """Returns the authenticated user's current knowledge graph."""
    return get_service().get_graph(user_id)


@app.post("/graph/rebuild")
def rebuild_graph_endpoint(user_id: str = Depends(get_current_user_id)) -> dict:
    """Rebuilds the authenticated user's knowledge graph from their current content."""
    return get_service().build_graph(user_id)


@app.delete("/graph")
def delete_graph_endpoint(user_id: str = Depends(get_current_user_id)) -> dict:
    """Deletes all graph edges for the authenticated user."""
    return get_service().delete_graph(user_id)
