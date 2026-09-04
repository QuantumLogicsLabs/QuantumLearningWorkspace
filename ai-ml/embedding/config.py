"""
Central configuration for the embedding module.

All values are read from environment variables (via a .env file) so
no secrets are hard-coded. Copy .env.example to .env and fill in your
own keys before running anything.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes")


@dataclass
class Settings:
    # ---------------- MongoDB ----------------
    # Free tier: MongoDB Atlas free "M0" cluster (512MB, no cost, no card
    # required for the free tier). Or run mongodb locally for $0.
    mongodb_uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    mongodb_db: str = field(default_factory=lambda: os.getenv("MONGODB_DB", "studymind"))
    mongodb_collection: str = field(default_factory=lambda: os.getenv("MONGODB_COLLECTION", "chunks"))

    # ---------------- Pinecone ----------------
    # Free tier: Pinecone Starter plan (serverless, no card required for
    # light usage as of this writing — always confirm current limits at
    # https://www.pinecone.io/pricing/ since free-tier terms can change).
    pinecone_api_key: str = field(default_factory=lambda: os.getenv("PINECONE_API_KEY", ""))
    pinecone_index_name: str = field(default_factory=lambda: os.getenv("PINECONE_INDEX_NAME", "studymind-embeddings"))
    pinecone_cloud: str = field(default_factory=lambda: os.getenv("PINECONE_CLOUD", "aws"))
    pinecone_region: str = field(default_factory=lambda: os.getenv("PINECONE_REGION", "us-east-1"))
    pinecone_metric: str = field(default_factory=lambda: os.getenv("PINECONE_METRIC", "cosine"))

    # ---------------- Embedding model ----------------
    # sentence-transformers runs 100% locally (downloads weights once,
    # then no API key / no per-call cost / no internet needed after that).
    # all-MiniLM-L6-v2 -> 384 dimensions, fast, good quality for RAG.
    embedding_model_name: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"))
    embedding_dimension: int = field(default_factory=lambda: int(os.getenv("EMBEDDING_DIMENSION", "384")))

    # ---------------- Chunking ----------------
    chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "300")))     # words per chunk
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "50")))  # overlap in words
    
settings = Settings()

