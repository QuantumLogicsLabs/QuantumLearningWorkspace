"""
[P1-5] Cross-module isolation and lifecycle tests for the shared
content store (embedding/chroma_store.py) — the store P0-1 unified
ingestion and quiz retrieval onto.

These test the storage layer directly rather than through an HTTP
endpoint, since P0-5's purge endpoint isn't built yet. The
underlying function it will eventually wrap — delete_chunks() — was
already added as part of P0-1, and that's what "purge" is tested
against here. If/when P0-5's endpoint exists, it should just be a
thin HTTP wrapper around this same function, so these tests remain
valid underneath it.

No GROQ_API_KEY or any other secret is needed — nothing here touches
quiz generation or the LLM, only storage.
"""

import pytest

from embedding import chroma_store


@pytest.fixture
def tmp_chroma(tmp_path, monkeypatch):
    """
    Points chroma_store at a fresh, empty temp directory for the
    duration of one test, so tests never touch the real
    shared_chroma_data/ and never see each other's data.
    """
    monkeypatch.setattr(chroma_store, "DEFAULT_CHROMA_PATH", str(tmp_path))
    return tmp_path


def _chunks(*texts):
    return [{"chunk_index": i, "text": t} for i, t in enumerate(texts)]


# ---------------------------------------------------------------
# User isolation
# ---------------------------------------------------------------

def test_user_a_cannot_see_user_b_content(tmp_chroma):
    chroma_store.store_chunks(
        _chunks("Photosynthesis occurs in the chloroplast."),
        user_id="userA", document_id="docA", title="Bio Notes A",
    )
    chroma_store.store_chunks(
        _chunks("Mitochondria is the powerhouse of the cell."),
        user_id="userB", document_id="docB", title="Bio Notes B",
    )

    results_a = chroma_store.query_chunks("cell biology", top_k=5, user_id="userA")
    results_b = chroma_store.query_chunks("cell biology", top_k=5, user_id="userB")

    assert len(results_a) > 0
    assert len(results_b) > 0
    assert all(r["metadata"]["user_id"] == "userA" for r in results_a)
    assert all(r["metadata"]["user_id"] == "userB" for r in results_b)
    assert not any(r["metadata"]["document_id"] == "docB" for r in results_a)
    assert not any(r["metadata"]["document_id"] == "docA" for r in results_b)


def test_unscoped_search_sees_both_users_when_no_filter_given(tmp_chroma):
    """
    Documents today's default: with no user_id passed, search is
    unscoped. Enforcing the filter at the caller level (quiz_service.py
    always passing an authenticated user_id) is P0-3's job, not this
    function's — this test exists so a future accidental change to
    that default doesn't slip by unnoticed.
    """
    chroma_store.store_chunks(_chunks("Content from A"), user_id="userA", document_id="docA", title="A")
    chroma_store.store_chunks(_chunks("Content from B"), user_id="userB", document_id="docB", title="B")

    results = chroma_store.query_chunks("content", top_k=10)
    seen_users = {r["metadata"]["user_id"] for r in results}

    assert seen_users == {"userA", "userB"}


# ---------------------------------------------------------------
# Document filtering
# ---------------------------------------------------------------

def test_document_id_filter_returns_only_that_document(tmp_chroma):
    chroma_store.store_chunks(
        _chunks("First document content about volcanoes."),
        user_id="userA", document_id="doc1", title="Doc 1",
    )
    chroma_store.store_chunks(
        _chunks("Second document content about earthquakes."),
        user_id="userA", document_id="doc2", title="Doc 2",
    )

    results = chroma_store.query_chunks("geology", top_k=10, document_id="doc1")

    assert len(results) > 0
    assert all(r["metadata"]["document_id"] == "doc1" for r in results)


# ---------------------------------------------------------------
# Duplicate ingest
# ---------------------------------------------------------------

def test_duplicate_ingest_same_document_id_does_not_duplicate_chunks(tmp_chroma):
    """
    Re-ingesting the same document_id (e.g. a user re-uploads the same
    file) must upsert, not append — chunk ids are deterministic
    (f"{document_id}_chunk{index}"), so this should never double-count.
    """
    chunks = _chunks("Same content ingested twice.")

    chroma_store.store_chunks(chunks, user_id="userA", document_id="dup-doc", title="Dup")
    chroma_store.store_chunks(chunks, user_id="userA", document_id="dup-doc", title="Dup")

    collection = chroma_store.get_collection()
    stored = collection.get(where={"document_id": "dup-doc"})

    assert len(stored["ids"]) == 1


# ---------------------------------------------------------------
# Purge / lifecycle
# ---------------------------------------------------------------

def test_purge_removes_all_chunks_for_document(tmp_chroma):
    chroma_store.store_chunks(
        _chunks("Chunk one.", "Chunk two."),
        user_id="userA", document_id="to-delete", title="Delete Me",
    )

    before = chroma_store.query_chunks("chunk", top_k=10, document_id="to-delete")
    assert len(before) == 2

    chroma_store.delete_chunks("to-delete")

    after = chroma_store.query_chunks("chunk", top_k=10, document_id="to-delete")
    assert len(after) == 0


def test_purge_is_safe_to_call_twice(tmp_chroma):
    """Matches P0-5's DoD language ('safe to call twice') at the
    storage-function level, ahead of the HTTP endpoint existing."""
    chroma_store.store_chunks(
        _chunks("Some content."),
        user_id="userA", document_id="idempotent-doc", title="Idempotent",
    )

    chroma_store.delete_chunks("idempotent-doc")
    chroma_store.delete_chunks("idempotent-doc")  # must not raise

    after = chroma_store.query_chunks("content", top_k=10, document_id="idempotent-doc")
    assert len(after) == 0


def test_purge_only_affects_the_targeted_document(tmp_chroma):
    chroma_store.store_chunks(_chunks("Keep me."), user_id="userA", document_id="keep", title="Keep")
    chroma_store.store_chunks(_chunks("Delete me."), user_id="userA", document_id="delete", title="Delete")

    chroma_store.delete_chunks("delete")

    remaining = chroma_store.query_chunks("keep delete", top_k=10)
    remaining_doc_ids = {r["metadata"]["document_id"] for r in remaining}

    assert "keep" in remaining_doc_ids
    assert "delete" not in remaining_doc_ids
