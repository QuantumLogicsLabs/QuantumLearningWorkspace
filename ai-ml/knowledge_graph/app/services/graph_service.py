"""
Main integration interface for the knowledge graph module — what
api/graph_routes.py and any other module calls.

user_id is accepted as an explicit parameter on every method here
(not sourced from a request/token internally), so this class stays
easy to unit test with any user_id value. Only the API layer
(api/graph_routes.py) is responsible for sourcing a real, verified
user_id from a JWT before calling into this service.
"""
from knowledge_graph.app.validators.graph_validators import validate_user_id
from knowledge_graph.app.builders.document_graph_builder import build_document_graph, get_user_documents
from knowledge_graph.app.builders.topic_graph_builder import build_topic_graph
from knowledge_graph.app.storage import graph_store


class GraphService:
    def build_graph(self, user_id: str, include_topics: bool = True) -> dict:
        """
        Builds (or rebuilds) this user's full graph and persists it.
        Returns a summary dict, not the full graph — call get_graph()
        to read it back.
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

    def get_graph(self, user_id: str) -> dict:
        """
        Returns { "nodes": [...], "edges": [...] } for this user,
        combining both document- and topic-level edges. Nodes are
        derived from the user's currently embedded documents, so the
        node list always reflects current content even if the graph
        hasn't been rebuilt since the last edit.
        """
        validate_user_id(user_id)

        docs = get_user_documents(user_id)
        nodes = [
            {"id": doc_id, "title": data["title"], "node_type": "document"}
            for doc_id, data in docs.items()
        ]

        edges = graph_store.get_edges(user_id)

        return {"nodes": nodes, "edges": edges}

    def delete_graph(self, user_id: str) -> dict:
        validate_user_id(user_id)
        graph_store.delete_edges(user_id)
        return {"user_id": user_id, "deleted": True}
