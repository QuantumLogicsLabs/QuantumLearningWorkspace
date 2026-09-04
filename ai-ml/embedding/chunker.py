"""
Splits ingested document text (the common ingestion schema:
{ source_type, title, text, metadata }) into overlapping,
word-based chunks ready for embedding.
"""

from embedding.config import settings


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list:
    """
    Word-based sliding-window chunking with overlap.

    Returns a list of:
      { "chunk_index": int, "text": str, "start_word": int, "end_word": int }
    """
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    words = text.split()
    if not words:
        return []

    step = chunk_size - overlap
    chunks = []
    start = 0
    index = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append({
            "chunk_index": index,
            "text": " ".join(words[start:end]),
            "start_word": start,
            "end_word": end,
        })
        index += 1
        if end == len(words):
            break
        start += step

    return chunks


def chunk_document(document: dict, chunk_size: int = None, overlap: int = None) -> list:
    """
    document: common ingestion schema dict, e.g.
      {
        "source_type": "pdf" | "youtube" | "article",
        "title": "...",
        "text": "...",
        "metadata": {"author": "", "date": "", "source": ""}
      }

    Returns chunk dicts enriched with the parent document's title,
    source_type, and metadata, ready to be embedded and stored.
    """
    raw_chunks = chunk_text(document.get("text", ""), chunk_size, overlap)

    return [
        {
            **c,
            "title": document.get("title", ""),
            "source_type": document.get("source_type", ""),
            "metadata": document.get("metadata", {}),
        }
        for c in raw_chunks
    ]
