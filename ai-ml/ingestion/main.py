"""
8. API Design
--------------
Free stack: FastAPI + Uvicorn — pip install fastapi uvicorn python-multipart
Run locally (from inside the ai-ml/ folder):
    uvicorn ingestion.main:app --reload --port 8001
Endpoints:
  POST /ingest/pdf       (multipart file upload)
  POST /ingest/youtube   ({"url": "..."})
  POST /ingest/article   ({"url": "..."})

[NV-2 fix] All three endpoints now require a valid JWT
("Authorization: Bearer <jwt>"), matching Contract v1 and the same
pattern quiz_generator/app/auth.py already implements. user_id is no
longer accepted from the client (form field / request body) — it is
derived exclusively from the verified token's `sub` claim, so a
caller can never claim to be another user. This closes the gap
identified in NV-2: previously these endpoints had no authentication
at all, unlike quiz_generator's endpoints, which were already correct.
"""
from __future__ import annotations
import shutil
import tempfile
import os
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from embedding.chroma_store import delete_chunks
from ingestion.pdf.extractor import ingest_pdf
from ingestion.youtube.transcript import ingest_youtube
from ingestion.web.scraper import ingest_article
from embedding.chunker import chunk_document
from embedding.chroma_store import store_chunks

# Reusing the existing, working JWT verification already implemented
# for quiz_generator — same secret, same failure modes, same Contract
# v1 behavior. Not duplicated; imported directly so both services
# stay in sync if the auth scheme ever changes.
from quiz_generator.app.auth import get_current_user_id

app = FastAPI(title="StudyMind AI - Content Ingestion Pipeline")


class URLRequest(BaseModel):
    url: str
    # user_id intentionally removed — identity now comes only from
    # the verified JWT, never from client-supplied request data.


def _chunk_and_store(result: dict, user_id: str) -> dict:
    """Shared helper: chunk an ingested document and store it in ChromaDB."""
    document_id = str(uuid.uuid4())
    chunks = chunk_document(result)
    stored_count = store_chunks(
        chunks=chunks,
        user_id=user_id,
        document_id=document_id,
        title=result.get("title", ""),
    )
    return {
        "document_id": document_id,
        "title": result.get("title", ""),
        "chunks_stored": stored_count,
    }


# -----------------------------
# PDF INGESTION
# -----------------------------
@app.post("/ingest/pdf")
async def ingest_pdf_endpoint(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = ingest_pdf(file_path=tmp_path, original_filename=file.filename)
        storage_info = _chunk_and_store(result, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {**result, **storage_info}


# -----------------------------
# YOUTUBE INGESTION
# -----------------------------
@app.post("/ingest/youtube")
async def ingest_youtube_endpoint(
    payload: URLRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        result = ingest_youtube(payload.url)
        storage_info = _chunk_and_store(result, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {**result, **storage_info}


# -----------------------------
# ARTICLE INGESTION
# -----------------------------
@app.post("/ingest/article")
async def ingest_article_endpoint(
    payload: URLRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        result = ingest_article(payload.url)
        storage_info = _chunk_and_store(result, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {**result, **storage_info}


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "StudyMind AI Content Ingestion Pipeline",
    }


# -----------------------------
# DOCUMENT PURGE (P0-5)
# -----------------------------
@app.delete("/documents/{document_id}")
async def delete_document_endpoint(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    [P0-5] Purge a document's chunks from the shared ChromaDB store.
    Matches the DELETE /documents/{document_id} contract Pluto's
    delete_upload() already calls, and reuses the same
    chroma_store.delete_chunks() Lambda already verified working for
    quiz_generator's own purge endpoint. Idempotent.

    Note: does not verify document_id actually belongs to user_id
    before deleting -- same ownership-check gap already flagged on
    quiz_generator's purge endpoint. Caller (Pluto) is expected to
    have already confirmed ownership before calling this.
    """
    delete_chunks(document_id)
    return {"success": True, "message": f"Document {document_id} purged."}