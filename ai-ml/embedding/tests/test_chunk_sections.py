"""
Vector-storage tests for the new file formats: section-aware chunking
(slides, spreadsheet row blocks), short and empty documents, and the
extra metadata (source_type, section) stored with each chunk.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import embedding.chroma_store as chroma_store  # noqa: E402
from embedding.chunker import chunk_document, chunk_sections, chunk_text  # noqa: E402


def _words(n, prefix="w"):
    return " ".join(f"{prefix}{i}" for i in range(n))


# ---------- section packing ----------

def test_small_sections_are_packed_whole_into_one_chunk():
    sections = [
        {"label": "Slide 1", "text": _words(10, "a")},
        {"label": "Slide 2", "text": _words(10, "b")},
        {"label": "Slide 3", "text": _words(10, "c")},
    ]
    chunks = chunk_sections(sections, chunk_size=50, overlap=5)
    assert len(chunks) == 1
    assert chunks[0]["section"] == "Slide 1 - Slide 3"
    assert chunks[0]["start_word"] == 0 and chunks[0]["end_word"] == 30


def test_a_section_is_never_cut_when_it_fits_in_a_chunk():
    sections = [
        {"label": "Slide 1", "text": _words(30, "a")},
        {"label": "Slide 2", "text": _words(30, "b")},
        {"label": "Slide 3", "text": _words(30, "c")},
    ]
    chunks = chunk_sections(sections, chunk_size=50, overlap=5)
    # 30 + 30 > 50, so every slide gets its own chunk, each one intact
    assert [c["section"] for c in chunks] == ["Slide 1", "Slide 2", "Slide 3"]
    assert [len(c["text"].split()) for c in chunks] == [30, 30, 30]
    assert [c["chunk_index"] for c in chunks] == [0, 1, 2]


def test_an_oversized_section_is_split_and_keeps_its_label():
    sections = [{"label": "Sheet1", "text": _words(120)}]
    chunks = chunk_sections(sections, chunk_size=50, overlap=10)
    assert len(chunks) > 1
    assert all(c["section"] == "Sheet1" for c in chunks)
    assert all(len(c["text"].split()) <= 50 for c in chunks)


def test_empty_sections_are_skipped():
    sections = [
        {"label": "Slide 1", "text": "   "},
        {"label": "Slide 2", "text": _words(5)},
        {"label": "Slide 3", "text": None},
    ]
    chunks = chunk_sections(sections, chunk_size=50, overlap=5)
    assert len(chunks) == 1 and chunks[0]["section"] == "Slide 2"


# ---------- chunk_document behaviour ----------

def test_document_without_sections_behaves_as_before():
    doc = {"source_type": "txt", "title": "t", "text": _words(400), "metadata": {}}
    chunks = chunk_document(doc, chunk_size=300, overlap=50)
    assert len(chunks) == 2
    assert all("section" not in c for c in chunks)
    assert chunks[0]["source_type"] == "txt" and chunks[0]["title"] == "t"


def test_sections_are_used_when_present_and_text_is_the_fallback():
    doc = {
        "source_type": "pptx", "title": "deck", "text": _words(20),
        "metadata": {},
        "sections": [{"label": "Slide 1", "text": _words(20)}],
    }
    chunks = chunk_document(doc, chunk_size=300, overlap=50)
    assert chunks[0]["section"] == "Slide 1"

    doc["sections"] = [{"label": "Slide 1", "text": ""}]   # nothing usable in sections
    chunks = chunk_document(doc, chunk_size=300, overlap=50)
    assert len(chunks) == 1 and "section" not in chunks[0]


def test_short_document_still_produces_one_chunk():
    doc = {"source_type": "docx", "title": "Offer letter",
           "text": "Dear candidate, we are pleased to offer you the position.", "metadata": {}}
    assert len(chunk_document(doc)) == 1


def test_empty_document_produces_no_chunks():
    assert chunk_document({"source_type": "txt", "title": "x", "text": "  \n ", "metadata": {}}) == []


def test_zero_overlap_is_respected():
    chunks = chunk_text(_words(100), chunk_size=40, overlap=0)
    assert [(c["start_word"], c["end_word"]) for c in chunks] == [(0, 40), (40, 80), (80, 100)]


# ---------- metadata stored in Chroma ----------

class _Vectors(list):
    def tolist(self):
        return list(self)


class _FakeModel:
    def encode(self, texts):
        return _Vectors([[0.0, 0.0] for _ in texts])


class _FakeCollection:
    def __init__(self):
        self.rows = {}

    def upsert(self, ids, embeddings, documents, metadatas):
        for i, chunk_id in enumerate(ids):
            self.rows[chunk_id] = (documents[i], metadatas[i])


def _store(monkeypatch, doc, document_id="doc-1"):
    collection = _FakeCollection()
    monkeypatch.setattr(chroma_store, "get_collection", lambda *a, **k: collection)
    monkeypatch.setattr(chroma_store, "get_embedding_model", lambda: _FakeModel())
    chunks = chunk_document(doc, chunk_size=50, overlap=5)
    chroma_store.store_chunks(chunks, user_id="a@x.com", document_id=document_id, title=doc["title"])
    return collection


def test_stored_chunks_carry_source_type_and_section(monkeypatch):
    doc = {
        "source_type": "pptx", "title": "deck", "metadata": {}, "text": "",
        "sections": [{"label": "Slide 1", "text": _words(30)}, {"label": "Slide 2", "text": _words(30)}],
    }
    collection = _store(monkeypatch, doc)
    metas = [m for _, m in collection.rows.values()]
    assert {m["section"] for m in metas} == {"Slide 1", "Slide 2"}
    assert all(m["source_type"] == "pptx" for m in metas)
    assert all(m["user_id"] == "a@x.com" and m["document_id"] == "doc-1" and m["document"] == "deck" for m in metas)


def test_optional_tags_are_left_out_not_stored_as_empty(monkeypatch):
    doc = {"title": "plain", "text": _words(20), "metadata": {}}   # no source_type, no sections
    collection = _store(monkeypatch, doc)
    for _, meta in collection.rows.values():
        assert "section" not in meta and "source_type" not in meta
        assert None not in meta.values()   # Chroma rejects None metadata values
