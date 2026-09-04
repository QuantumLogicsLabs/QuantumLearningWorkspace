"""
Builds finer-grained edges between individual chunks ("topics"),
within and across a user's documents — the detail layer the
document-level graph misses.
"""
from itertools import combinations

from knowledge_graph.app.config import SIMILARITY_THRESHOLD_TOPIC
from knowledge_graph.app.utils.similarity import cosine_similarity
from knowledge_graph.app.utils.topic_labeler import generate_label
from knowledge_graph.app.models.graph_edge import GraphEdge
from knowledge_graph.app.builders.document_graph_builder import get_user_documents


def build_topic_graph(user_id: str, max_chunks: int = 200) -> list:
    """
    Returns a list of GraphEdge.to_dict() for chunk-level relationships.

    max_chunks caps how many of the user's chunks are compared, since
    comparing every pair is O(n^2) — protects against runaway cost for
    users with very large amounts of content. Chunks beyond the cap
    are simply not included in this pass.
    """
    docs = get_user_documents(user_id)

    # flatten into a single list of (chunk_id, vector, text, title)
    chunks = []
    for doc_id, data in docs.items():
        for i, (vector, text) in enumerate(zip(data["vectors"], data["texts"])):
            chunks.append({
                "chunk_id": f"{doc_id}_{i}",
                "vector": vector,
                "text": text,
                "title": data["title"],
            })

    chunks = chunks[:max_chunks]

    edges = []
    for a, b in combinations(chunks, 2):
        score = cosine_similarity(a["vector"], b["vector"])
        if score >= SIMILARITY_THRESHOLD_TOPIC:
            edge = GraphEdge(
                user_id=user_id,
                source_id=a["chunk_id"],
                target_id=b["chunk_id"],
                node_type="topic",
                similarity=round(score, 4),
                source_title=a["title"],
                target_title=b["title"],
                label=generate_label(a["text"], b["text"]),
            )
            edges.append(edge.to_dict())

    return edges
