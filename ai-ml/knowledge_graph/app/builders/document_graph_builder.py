"""
Builds document-to-document edges: groups a user's chunks by
document, averages each document's chunk vectors, compares every
pair of documents, and creates an edge wherever similarity is above
the configured threshold.
"""
from itertools import combinations

from embedding.chroma_store import get_collection
from knowledge_graph.app.config import SIMILARITY_THRESHOLD_DOCUMENT, CONTENT_COLLECTION_NAME
from knowledge_graph.app.utils.vectorizer import get_document_vector
from knowledge_graph.app.utils.similarity import cosine_similarity
from knowledge_graph.app.utils.topic_labeler import generate_label
from knowledge_graph.app.validators.graph_validators import validate_documents_have_vectors
from knowledge_graph.app.models.graph_edge import GraphEdge


def get_user_documents(user_id: str) -> dict:
    """
    Fetches this user's chunks from the shared ChromaDB collection and
    groups them by document_id.

    Returns: { document_id: {"title": str, "vectors": [...], "texts": [...]} }
    """
    collection = get_collection(name=CONTENT_COLLECTION_NAME)
    result = collection.get(
        where={"user_id": user_id},
        include=["embeddings", "documents", "metadatas"],
    )

    docs: dict = {}
    ids = result.get("ids", [])
    embeddings = result.get("embeddings", [])
    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])

    for i in range(len(ids)):
        meta = metadatas[i] or {}
        doc_id = meta.get("document_id")
        if not doc_id:
            continue
        docs.setdefault(doc_id, {"title": meta.get("document", ""), "vectors": [], "texts": []})
        docs[doc_id]["vectors"].append(embeddings[i])
        docs[doc_id]["texts"].append(documents[i])

    return docs


def build_document_graph(user_id: str) -> list:
    """
    Returns a list of GraphEdge.to_dict() for this user's
    document-to-document relationships.
    """
    docs = validate_documents_have_vectors(get_user_documents(user_id))

    doc_vectors = {
        doc_id: get_document_vector(data["vectors"])
        for doc_id, data in docs.items()
    }

    edges = []
    for (id_a, vec_a), (id_b, vec_b) in combinations(doc_vectors.items(), 2):
        score = cosine_similarity(vec_a, vec_b)
        if score >= SIMILARITY_THRESHOLD_DOCUMENT:
            # label from a sample of each document's text, not the full text
            sample_a = " ".join(docs[id_a]["texts"][:2])
            sample_b = " ".join(docs[id_b]["texts"][:2])

            edge = GraphEdge(
                user_id=user_id,
                source_id=id_a,
                target_id=id_b,
                node_type="document",
                similarity=round(score, 4),
                source_title=docs[id_a]["title"],
                target_title=docs[id_b]["title"],
                label=generate_label(sample_a, sample_b),
            )
            edges.append(edge.to_dict())

    return edges
