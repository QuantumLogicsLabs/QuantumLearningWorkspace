"""
Shared ChromaDB store — the single canonical content store for both
the ingestion pipeline and quiz generation.

[P0-1 fix] Previously, quiz generation queried Pinecone + MongoDB
(see the old embedder.py) while ingestion wrote here. The two never
overlapped, so newly ingested content was invisible to quiz
generation. This file is now the ONLY storage path for both:
ingestion calls store_chunks() (unchanged), and quiz generation's
Embedder.search() calls query_chunks() (new) instead of touching
Pinecone/Mongo at all.

Also fixes a subtler bug: this module used to load its own separate
SentenceTransformer instance with default (non-normalized) output,
while embedding/model.py's shared model normalizes its vectors. Two
different embedding configs writing into the same cosine-similarity
space would have produced quietly wrong nearest-neighbor results.
Both reads and writes now go through the one shared, normalized
model in model.py.
"""
from __future__ import annotations
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv

from embedding.model import get_embedding_model

# [Fix] This file lives at ai-ml/embedding/chroma_store.py — two
# .parent calls reach ai-ml/, which is where .env actually lives.
# The previous three .parent calls pointed one level too high (the
# repo root), where no .env exists at all, so CHROMA_API_KEY /
# CHROMA_TENANT / CHROMA_DATABASE (and anything else loaded here)
# were silently never found regardless of what was in ai-ml/.env.
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


DEFAULT_COLLECTION_NAME = "study_chunks"


def get_collection(name: str = DEFAULT_COLLECTION_NAME, path: str = None):
    client = chromadb.CloudClient(
        api_key=os.getenv("CHROMA_API_KEY"),
        tenant=os.getenv("CHROMA_TENANT"),
        database=os.getenv("CHROMA_DATABASE"),
    )
    return client.get_or_create_collection(name=name)


def store_chunks(chunks: list[dict], user_id: str, document_id: str, title: str) -> int:
    """
    Embed and store chunks in the shared ChromaDB collection.

    chunks: list of dicts from chunker.chunk_document(), each with a "text" key.
    Returns the number of chunks stored.
    """
    if not chunks:
        return 0

    collection = get_collection()
    model = get_embedding_model()  # shared, normalized model — same one queries use

    ids = [f"{document_id}_chunk{c['chunk_index']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "user_id": user_id,
            "document_id": document_id,
            "document": title,
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]
    embeddings = model.encode(documents)  # list[list[float]], already normalized

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    return len(chunks)


def query_chunks(
    query_text: str,
    top_k: int = 5,
    user_id: str = None,
    document_id: str = None,
) -> list:
    """
    [P0-1 new] Embed a query and return the top_k nearest chunks from
    the shared collection, in the shape quiz_service.py expects:
        [{"score": float, "text": str, "title": str, "metadata": dict}, ...]

    user_id / document_id, if given, are applied as an exact-match
    metadata filter (ChromaDB's `where`). Both default to None (no
    filter) today, which preserves current unscoped behavior — this
    is deliberately plumbed through now so P0-3 (user-scoped quiz
    retrieval) can pass user_id here without another storage change.
    """
    collection = get_collection()
    model = get_embedding_model()

    where = {}
    if user_id is not None:
        where["user_id"] = user_id
    if document_id is not None:
        where["document_id"] = document_id

    query_embedding = model.encode(query_text)[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where or None,
    )

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output = []
    for i in range(len(ids)):
        meta = metadatas[i] or {}
        output.append({
            "score": distances[i],
            "text": documents[i],
            "title": meta.get("document", ""),
            "metadata": meta,
        })
    return output


def delete_chunks(document_id: str) -> None:
    """
    [P0-1 new] Remove all chunks belonging to a document from the
    shared collection. Chroma's delete-by-filter is idempotent
    (deleting a non-existent id/filter is a no-op), which is also
    what P0-5's purge endpoint will need.
    """
    collection = get_collection()
    collection.delete(where={"document_id": document_id})


def get_document_chunks(document_id: str, user_id: str = None) -> list:
    """
    [Roadmap multi-mode] Returns all chunk texts for a document — a
    direct metadata lookup, not a similarity search (unlike
    query_chunks). Used for mode="document" roadmap generation, where
    the whole document's content is needed, not just the top-k
    results for some query.

    If user_id is given, only chunks whose stored user_id matches are
    returned — this prevents a caller from pulling another user's
    document content by guessing/supplying a document_id that isn't
    theirs. Returns an empty list if the document doesn't exist, or
    exists but belongs to a different user (the two cases are
    intentionally indistinguishable to the caller).
    """
    collection = get_collection()

    where = {"document_id": document_id}
    if user_id is not None:
        where = {"$and": [{"document_id": document_id}, {"user_id": user_id}]}

    results = collection.get(where=where)
    return results.get("documents", []) or []