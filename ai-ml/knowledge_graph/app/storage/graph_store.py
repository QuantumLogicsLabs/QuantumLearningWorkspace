"""
Stores graph edges as a JSON file inside the same shared data
directory ChromaDB already uses (CHROMA_DB_PATH). This is
deliberately not a new database technology — edges are small,
relationship-only records, so a flat JSON file keeps this module
free of new infrastructure dependencies while still living
alongside the "one shared data location" the rest of the project
already uses.

Not safe for many concurrent writers, but fine for how this module
is used today: rebuilt on-demand per user, not written to under
sustained concurrent load.
"""
import json
import os
from pathlib import Path
from threading import Lock

from knowledge_graph.app.config import CHROMA_DB_PATH

_EDGES_FILENAME = "knowledge_graph_edges.json"
_lock = Lock()


def _edges_path() -> Path:
    return Path(CHROMA_DB_PATH) / _EDGES_FILENAME


def _read_all() -> list:
    path = _edges_path()
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_all(edges: list) -> None:
    path = _edges_path()
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(edges, f, indent=2)


def save_edges(user_id: str, edges: list, node_type: str) -> int:
    """
    Replaces all existing edges of the given node_type for this user
    with the new set (a full rebuild, not an incremental append —
    keeps the graph consistent with the latest embedded content).
    edges: list of GraphEdge.to_dict() results.
    Returns the number of edges written.
    """
    with _lock:
        all_edges = _read_all()
        # drop this user's existing edges of this type, keep everyone else's
        all_edges = [
            e for e in all_edges
            if not (e["user_id"] == user_id and e["node_type"] == node_type)
        ]
        all_edges.extend(edges)
        _write_all(all_edges)
    return len(edges)


def get_edges(user_id: str, node_type: str = None) -> list:
    all_edges = _read_all()
    result = [e for e in all_edges if e["user_id"] == user_id]
    if node_type:
        result = [e for e in result if e["node_type"] == node_type]
    return result


def delete_edges(user_id: str) -> None:
    with _lock:
        all_edges = _read_all()
        all_edges = [e for e in all_edges if e["user_id"] != user_id]
        _write_all(all_edges)
