"""
Represents a single node in the knowledge graph — either a whole
document, or (for the topic-level graph) an individual chunk.
"""
from dataclasses import dataclass, asdict


@dataclass
class GraphNode:
    node_id: str          # document_id, or "documentid_chunkindex" for topic nodes
    node_type: str         # "document" or "topic"
    title: str
    user_id: str

    def to_dict(self) -> dict:
        return asdict(self)
