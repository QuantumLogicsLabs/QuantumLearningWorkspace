"""
Configuration for the knowledge graph module.

Reuses the shared .env at the ai-ml/ root, same pattern as
embedding/config.py and quiz_generator/app/auth.py.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ai-ml/.env  (app -> knowledge-graph -> ai-ml)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

# --- Similarity thresholds ---
# Document-level pairs below this score are not considered related.
SIMILARITY_THRESHOLD_DOCUMENT = float(os.getenv("KG_DOC_SIMILARITY_THRESHOLD", "0.5"))

# Topic/chunk-level pairs below this score are not considered related.
# Slightly higher than the document threshold, since chunk-level
# comparisons are noisier (less text per vector).
SIMILARITY_THRESHOLD_TOPIC = float(os.getenv("KG_TOPIC_SIMILARITY_THRESHOLD", "0.6"))

# --- Storage ---
# Reuses the same local ChromaDB path as embedding/chroma_store.py,
# so this module reads the same underlying data directory rather than
# introducing a second database location. Edge data is written to its
# own JSON file inside that same directory (see storage/graph_store.py) —
# not a new database technology, just a new file alongside Chroma's data.
CHROMA_DB_PATH = os.getenv(
    "CHROMA_DB_PATH",
    r"C:\Dev\QuantumLearningWorkspace\shared_chroma_data",
)
CONTENT_COLLECTION_NAME = "study_chunks"  # matches chroma_store.py's DEFAULT_COLLECTION_NAME

# --- API ---
API_PORT = int(os.getenv("KNOWLEDGE_GRAPH_PORT", "8005"))
