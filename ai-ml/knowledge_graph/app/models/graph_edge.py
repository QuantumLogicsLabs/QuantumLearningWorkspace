"""
Represents a relationship (edge) between two nodes in the graph.
"""
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class GraphEdge:
    user_id: str
    source_id: str
    target_id: str
    node_type: str          # "document" or "topic" — matches the nodes it connects
    similarity: float
    source_title: str
    target_title: str
    label: Optional[str] = None   # short human-readable reason for the connection

    def to_dict(self) -> dict:
        return asdict(self)
