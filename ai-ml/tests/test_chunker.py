import pytest
from embedding.chunker import chunk_document

def test_chunk_document_happy_path():
    """Verify document is split into chunks with correct metadata."""
    doc = {
        "source_type": "pdf",
        "title": "Lab Report",
        "text": "word1 " * 20, # 20 words
        "metadata": {"author": "Farwa"}
    }
    
    # Testing with small chunk size to force multiple chunks
    chunks = chunk_document(doc, chunk_size=10, overlap=2)
    
    assert len(chunks) > 1
    assert chunks[0]["title"] == "Lab Report"
    assert "chunk_index" in chunks[0]
    assert chunks[0]["metadata"]["author"] == "Farwa"

def test_chunk_document_empty_text():
    """Edge Case: Empty text should return empty list."""
    doc = {"text": "", "title": "Empty"}
    assert chunk_document(doc) == []