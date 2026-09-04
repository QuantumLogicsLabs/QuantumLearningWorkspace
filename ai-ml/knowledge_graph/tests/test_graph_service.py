"""
Integration tests for GraphService, against a real (ephemeral,
in-memory) ChromaDB collection — not mocked, so these catch real
wiring issues between the builders, storage, and Chroma.

Run: pytest knowledge_graph/tests/test_graph_service.py
"""
import numpy as np
import pytest

from embedding.chroma_store import get_collection
from knowledge_graph.app.services.graph_service import GraphService


def _make_vec(base: float, dim: int = 16, seed: int = 0) -> list:
    rng = np.random.default_rng(seed)
    return rng.normal(loc=base, scale=0.03, size=dim).tolist()


@pytest.fixture
def seeded_user(tmp_path):
    """Inserts two related documents and one unrelated document for a test user."""
    user_id = "pytest_user"
    collection = get_collection()

    rows = [
        ("docA", 0, "ML Basics", "Neural networks learn from data.", 0.8, 1),
        ("docA", 1, "ML Basics", "Training uses gradient descent.", 0.8, 2),
        ("docB", 0, "Deep Learning", "Gradient descent trains neural networks.", 0.82, 3),
        ("docC", 0, "Cooking", "Bread requires yeast and flour.", -0.8, 4),
    ]
    ids, embeddings, documents, metadatas = [], [], [], []
    for doc_id, idx, title, text, base, seed in rows:
        ids.append(f"{doc_id}_{idx}")
        embeddings.append(_make_vec(base, seed=seed))
        documents.append(text)
        metadatas.append({"user_id": user_id, "document_id": doc_id, "document": title, "chunk_index": idx})

    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    return user_id


def test_build_graph_links_related_documents(seeded_user):
    service = GraphService()
    result = service.build_graph(seeded_user)
    assert result["document_edges_created"] >= 1

    graph = service.get_graph(seeded_user)
    doc_edges = [e for e in graph["edges"] if e["node_type"] == "document"]
    titles = {(e["source_title"], e["target_title"]) for e in doc_edges}

    assert ("ML Basics", "Deep Learning") in titles or ("Deep Learning", "ML Basics") in titles


def test_build_graph_does_not_link_unrelated_documents(seeded_user):
    service = GraphService()
    service.build_graph(seeded_user)
    graph = service.get_graph(seeded_user)

    doc_edges = [e for e in graph["edges"] if e["node_type"] == "document"]
    cooking_involved = any(
        "Cooking" in (e["source_title"], e["target_title"]) for e in doc_edges
    )
    assert not cooking_involved


def test_get_graph_nodes_match_documents(seeded_user):
    service = GraphService()
    graph = service.get_graph(seeded_user)
    titles = {n["title"] for n in graph["nodes"]}
    assert titles == {"ML Basics", "Deep Learning", "Cooking"}


def test_delete_graph_clears_edges(seeded_user):
    service = GraphService()
    service.build_graph(seeded_user)
    service.delete_graph(seeded_user)

    graph = service.get_graph(seeded_user)
    assert graph["edges"] == []


def test_user_with_no_documents_does_not_crash():
    service = GraphService()
    result = service.build_graph("nobody_has_this_id")
    assert result["document_edges_created"] == 0
    assert result["topic_edges_created"] == 0


def test_empty_user_id_raises():
    service = GraphService()
    with pytest.raises(ValueError):
        service.get_graph("")
