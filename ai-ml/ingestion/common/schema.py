"""
Common Data Format
-------------------
Every ingestion module (documents / youtube / web) must return output
in this exact shape so downstream modules (chunking, embedding,
vector DB, RAG chatbot, quiz generation) can work without knowing
the original source.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Metadata:
    author: str = ""
    date: str = ""
    source: str = ""


@dataclass
class IngestResult:
    source_type: str          # File extension, "youtube", or "article"
    title: str
    text: str
    metadata: Metadata = field(default_factory=Metadata)

    def to_dict(self) -> dict:
        return asdict(self)


def build_result(source_type: str, title: str, text: str,
                  author: str = "", date: str = "", source: str = "") -> dict:
    """Convenience helper: build a common-format dict in one call."""
    result = IngestResult(
        source_type=source_type,
        title=title,
        text=text,
        metadata=Metadata(author=author, date=date, source=source),
    )
    return result.to_dict()
