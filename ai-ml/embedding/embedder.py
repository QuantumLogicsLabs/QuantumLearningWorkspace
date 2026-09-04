"""
Orchestrates document embedding + the search interface quiz
generation uses.

[P0-1 fix] This used to run its own parallel storage path — full
chunk text in MongoDB (source of truth) + vectors in Pinecone (for
search) — completely separate from ingestion's shared ChromaDB. That
meant anything ingested via ingestion/main.py was invisible to
QuizService.generate_quiz_from_topic(), since it searched Pinecone.

Everything now reads and writes the ONE shared ChromaDB collection
via chroma_store.py — the same collection ingestion already writes
to. No more Mongo/Pinecone clients, no more second indexing path.
"""

import uuid

from embedding.chunker import chunk_document
from embedding.chroma_store import store_chunks, query_chunks, delete_chunks

import argparse
import requests


class Embedder:
    def __init__(self):
        # No client setup needed here anymore — chroma_store.py owns
        # the one shared collection + embedding model as module-level
        # helpers, created fresh per call (see get_collection()).
        pass

    def embed_document(self, document: dict, user_id: str = "unknown") -> dict:
        """
        document: common ingestion schema
          { "source_type": ..., "title": ..., "text": ..., "metadata": {...} }

        Chunks it and stores it in the shared ChromaDB collection.
        Returns a small summary dict.

        Note: the normal ingestion request path (POST /ingest/pdf etc.)
        goes through ingestion/main.py's own _chunk_and_store(), which
        calls chroma_store.store_chunks() directly and doesn't use
        this method. This method exists for standalone/manual use
        (see the CLI at the bottom of this file) and now writes to the
        exact same store, so both paths stay consistent.
        """
        chunks = chunk_document(document)
        if not chunks:
            return {"document_id": None, "chunks_stored": 0}

        document_id = str(uuid.uuid4())
        stored_count = store_chunks(
            chunks=chunks,
            user_id=user_id,
            document_id=document_id,
            title=document.get("title", ""),
        )
        return {"document_id": document_id, "chunks_stored": stored_count}

    def search(
        self,
        query: str,
        top_k: int = 5,
        user_id: str = None,
        document_id: str = None,
    ) -> list:
        """
        Searches the shared ChromaDB collection — the same store
        ingestion writes to, so newly ingested content is immediately
        queryable here (P0-1's Definition of Done).

        user_id / document_id are optional scoping filters, passed
        straight through to chroma_store.query_chunks(). Left as None
        by default (unscoped), matching current QuizService behavior;
        P0-3 is what wires the caller-side enforcement of these.
        """
        return query_chunks(query, top_k=top_k, user_id=user_id, document_id=document_id)

    def delete_document(self, document_id: str, chunk_count: int = None):
        """
        Remove a document's chunks from the shared store.
        chunk_count is no longer needed (Chroma deletes by
        document_id metadata filter, not by reconstructing chunk ids)
        but is accepted for backward compatibility with existing callers.
        """
        delete_chunks(document_id)

    def close(self):
        """
        No-op now — chroma_store.py doesn't hold a persistent client
        connection open between calls, so there's nothing to close.
        Kept so existing callers (e.g. the CLI below) don't need to
        change.
        """
        pass


INGESTION_BASE_URL = "http://127.0.0.1:8001"
# NOTE: this was previously "http://127.0.0.1:8000", which is Mu's
# confirmed port, not Lambda ingestion's. Per the confirmed port
# scheme (Mu=8000, Pluto=5000, Lambda ingestion=8001, Lambda
# quiz=8002), 8001 is correct here. Flagging in case this was
# intentional for some other reason — worth a quick sanity check
# against P1-6's verification pass.


def _fetch_from_ingestion(pdf=None, youtube=None, article=None) -> dict:
    if pdf:
        with open(pdf, "rb") as f:
            response = requests.post(f"{INGESTION_BASE_URL}/ingest/pdf", files={"file": f})
    elif youtube:
        response = requests.post(f"{INGESTION_BASE_URL}/ingest/youtube", json={"url": youtube})
    elif article:
        response = requests.post(f"{INGESTION_BASE_URL}/ingest/article", json={"url": article})
    else:
        raise ValueError("Provide one of pdf, youtube, or article")

    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # python -m embedding.embedder --pdf path/to/file.pdf
    # python -m embedding.embedder --youtube "https://youtube.com/watch?v=..."
    # python -m embedding.embedder --article "https://example.com/article"
    # python -m embedding.embedder                (no args -> runs built-in sample test)

    parser = argparse.ArgumentParser(description="Run ingestion -> embedding end to end")
    parser.add_argument("--pdf", help="Path to a local PDF file")
    parser.add_argument("--youtube", help="YouTube video URL")
    parser.add_argument("--article", help="Web article URL")
    args = parser.parse_args()

    if args.pdf or args.youtube or args.article:
        print("Calling ingestion...")
        document = _fetch_from_ingestion(pdf=args.pdf, youtube=args.youtube, article=args.article)
        print(f"Ingestion returned title: {document.get('title', '(no title)')!r}")
        print(f"Text length: {len(document.get('text', ''))} characters")
    else:
        document = {
            "source_type": "article",
            "title": "Intro to Machine Learning",
            "text": (
                "Machine learning is a branch of artificial intelligence. "
                "It focuses on building systems that learn from data. "
                "Supervised learning uses labeled data to train models."
            ),
            "metadata": {"author": "", "date": "", "source": "https://example.com"},
        }

    embedder = Embedder()
    summary = embedder.embed_document(document, user_id="cli-test-user")
    print("Embedded:", summary)

    query = document.get("title") or document.get("text", "")[:50]
    results = embedder.search(query, top_k=3)
    for r in results:
        print(f"[{r['score']:.3f}] {r['text'][:100]}...")

    embedder.close()