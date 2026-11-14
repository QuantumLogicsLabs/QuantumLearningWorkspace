"""
Splits ingested document text (the common ingestion schema:
{ source_type, title, text, metadata, [sections] }) into overlapping,
word-based chunks ready for embedding.

Two modes:
  - Plain text (default): sliding word window with overlap.
  - Sections (optional): when a parser returns "sections" - a list of
    {"label": str, "text": str}, for example one entry per slide or per
    block of spreadsheet rows - whole sections are packed into chunks of
    up to chunk_size words and are only split when a single section is
    larger than one chunk. This keeps a slide or a table row from being
    cut in half. Documents without sections behave exactly as before.
"""

from embedding.config import settings


def _resolve(chunk_size, overlap):
    # "is None" (not "or") so an explicit overlap of 0 is respected.
    chunk_size = settings.chunk_size if chunk_size is None else chunk_size
    overlap = settings.chunk_overlap if overlap is None else overlap

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("chunk_overlap must not be negative")
    if overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    return chunk_size, overlap


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list:
    """
    Word-based sliding-window chunking with overlap.

    Returns a list of:
      { "chunk_index": int, "text": str, "start_word": int, "end_word": int }
    """
    chunk_size, overlap = _resolve(chunk_size, overlap)

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


def chunk_sections(sections: list, chunk_size: int = None, overlap: int = None) -> list:
    """
    Packs whole sections into chunks of at most chunk_size words.

    sections: [{"label": "Slide 3", "text": "..."}, ...]
    A section larger than chunk_size is split with the normal sliding
    window (and keeps its label). Empty sections are skipped.

    Returns a list of:
      { "chunk_index", "text", "start_word", "end_word", "section" }
    where "section" is the label of the first section in the chunk, or
    "first - last" when the chunk spans several sections.
    """
    chunk_size, overlap = _resolve(chunk_size, overlap)

    chunks = []
    buf = []            # [(label, text), ...] waiting to become one chunk
    buf_words = 0
    buf_start = 0       # word offset (in the whole document) where buf starts
    pos = 0             # word offset of the next section

    def emit(text, label, start, end):
        chunks.append({
            "chunk_index": len(chunks),
            "text": text,
            "start_word": start,
            "end_word": end,
            "section": label,
        })

    def flush():
        nonlocal buf, buf_words
        if buf:
            first, last = buf[0][0], buf[-1][0]
            label = first if first == last else f"{first} - {last}"
            emit("\n".join(t for _, t in buf), label, buf_start, buf_start + buf_words)
        buf, buf_words = [], 0

    for sec in sections:
        label = str(sec.get("label", ""))
        text = (sec.get("text") or "").strip()
        n = len(text.split())
        if n == 0:
            continue

        if n > chunk_size:
            flush()
            for piece in chunk_text(text, chunk_size, overlap):
                emit(piece["text"], label, pos + piece["start_word"], pos + piece["end_word"])
        else:
            if buf and buf_words + n > chunk_size:
                flush()
            if not buf:
                buf_start = pos
            buf.append((label, text))
            buf_words += n

        pos += n

    flush()
    return chunks


def chunk_document(document: dict, chunk_size: int = None, overlap: int = None) -> list:
    """
    document: common ingestion schema dict, e.g.
      {
        "source_type": "pdf" | "youtube" | "article" | "docx" | "xlsx" | ...,
        "title": "...",
        "text": "...",
        "metadata": {"author": "", "date": "", "source": ""},
        "sections": [{"label": "Slide 1", "text": "..."}]   # optional
      }

    Returns chunk dicts enriched with the parent document's title,
    source_type, and metadata, ready to be embedded and stored.
    """
    raw_chunks = []
    sections = document.get("sections")
    if sections:
        raw_chunks = chunk_sections(sections, chunk_size, overlap)
    if not raw_chunks:
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
