"""
Main integration interface for the knowledge graph module — what
api/graph_routes.py, ingestion, and any other module calls.

user_id is accepted as an explicit parameter on every method here
(not sourced from a request/token internally), so this class stays
easy to unit test with any user_id value. Only the API layer
(api/graph_routes.py) is responsible for sourcing a real, verified
user_id from a JWT before calling into this service.
"""
from knowledge_graph.app.validators.graph_validators import validate_user_id
from knowledge_graph.app.builders.document_graph_builder import build_document_graph, get_user_documents
from knowledge_graph.app.builders.topic_graph_builder import build_topic_graph
from knowledge_graph.app.utils.vectorizer import get_document_vector
from knowledge_graph.app.utils.similarity import cosine_similarity
from knowledge_graph.app.utils.topic_labeler import generate_label
from knowledge_graph.app.utils.relationship_classifier import classify_relationship
from knowledge_graph.app.utils.definition_generator import generate_definition
from knowledge_graph.app.config import SIMILARITY_THRESHOLD_DOCUMENT
from knowledge_graph.app.models.graph_edge import GraphEdge
from knowledge_graph.app.storage import graph_store, node_store


class GraphService:
    def build_graph(self, user_id: str, include_topics: bool = True) -> dict:
        """
        Full rebuild: recomputes ALL of this user's document (and
        optionally topic) edges from scratch, replacing whatever was
        stored before. Use add_document() instead for incrementally
        updating the graph after a single new upload — much cheaper,
        since it avoids re-classifying every existing pair.
        """
        validate_user_id(user_id)

        document_edges = build_document_graph(user_id)
        graph_store.save_edges(user_id, document_edges, node_type="document")

        topic_edge_count = 0
        if include_topics:
            topic_edges = build_topic_graph(user_id)
            graph_store.save_edges(user_id, topic_edges, node_type="topic")
            topic_edge_count = len(topic_edges)

        return {
            "user_id": user_id,
            "document_edges_created": len(document_edges),
            "topic_edges_created": topic_edge_count,
        }

    def add_document(self, user_id: str, document_id: str) -> dict:
        """
        [Task 5] Incrementally updates the graph after a single new
        document is embedded — compares only the new document against
        existing ones, rather than re-comparing every pair in the
        user's whole history. Avoids re-running LLM classification on
        unchanged pairs, so cost scales with new content, not the
        user's full document count.

        Safe to call even if document_id has no chunks yet, or if the
        user has no other documents to compare against — returns
        edges_created: 0 in either case rather than raising.
        """
        validate_user_id(user_id)

        docs = get_user_documents(user_id)
        if document_id not in docs or not docs[document_id]["vectors"]:
            return {"user_id": user_id, "document_id": document_id, "edges_created": 0}

        new_vector = get_document_vector(docs[document_id]["vectors"])
        new_title = docs[document_id]["title"]
        new_sample = " ".join(docs[document_id]["texts"][:2])

        # [Task 4] Generate this document's definition once, when it's
        # first added — not on every /graph read, to avoid an LLM call
        # per node per request.
        full_text = " ".join(docs[document_id]["texts"])
        definition = generate_definition(full_text)
        node_store.save_node_metadata(user_id, document_id, definition)

        existing_edges = graph_store.get_edges(user_id, node_type="document")
        new_edges = []

        for other_id, other_data in docs.items():
            if other_id == document_id:
                continue

            already_linked = any(
                {e["source_id"], e["target_id"]} == {document_id, other_id}
                for e in existing_edges
            )
            if already_linked:
                continue

            other_vector = get_document_vector(other_data["vectors"])
            score = cosine_similarity(new_vector, other_vector)

            if score >= SIMILARITY_THRESHOLD_DOCUMENT:
                other_sample = " ".join(other_data["texts"][:2])
                edge = GraphEdge(
                    user_id=user_id,
                    source_id=document_id,
                    target_id=other_id,
                    node_type="document",
                    similarity=round(score, 4),
                    source_title=new_title,
                    target_title=other_data["title"],
                    label=generate_label(new_sample, other_sample),
                    relationship_type=classify_relationship(new_sample, other_sample),
                )
                new_edges.append(edge.to_dict())

        if new_edges:
            graph_store.append_edges(user_id, new_edges, node_type="document")

        return {"user_id": user_id, "document_id": document_id, "edges_created": len(new_edges)}

    def get_graph(self, user_id: str, document_id: str = None) -> dict:
        """
        Returns { "nodes": [...], "edges": [...] } for this user,
        combining both document- and topic-level edges. Nodes are
        derived from the user's currently embedded documents, so the
        node list always reflects current content even if the graph
        hasn't been rebuilt since the last edit.

        [Objective 2] document_id, if given, filters the result to
        just that document plus its direct connections ("document
        mode") — omit it for the full graph (unchanged default
        behavior). No "topic mode" is implemented: a graph built from
        relationships between existing documents has no natural
        equivalent to a free-text topic input the way quiz/roadmap
        generation does — flagged to Pluto/Commander rather than
        forced.
        """
        validate_user_id(user_id)

        docs = get_user_documents(user_id)
        nodes = []
        for doc_id, data in docs.items():
            metadata = node_store.get_node_metadata(user_id, doc_id)
            nodes.append({
                "id": doc_id,
                "title": data["title"],
                "node_type": "document",
                "definition": metadata["definition"],
                "source_document": data["title"],
            })

        edges = graph_store.get_edges(user_id)

        if document_id:
            edges = [
                e for e in edges
                if document_id in (e["source_id"], e["target_id"])
                or e["source_id"].startswith(f"{document_id}_")
                or e["target_id"].startswith(f"{document_id}_")
            ]
            connected_ids = {document_id}
            for e in edges:
                connected_ids.add(e["source_id"].split("_")[0])
                connected_ids.add(e["target_id"].split("_")[0])
            nodes = [n for n in nodes if n["id"] in connected_ids]

        return {"nodes": nodes, "edges": edges}

    def delete_graph(self, user_id: str) -> dict:
        validate_user_id(user_id)
        graph_store.delete_edges(user_id)
        node_store.delete_node_metadata(user_id)
        return {"user_id": user_id, "deleted": True}