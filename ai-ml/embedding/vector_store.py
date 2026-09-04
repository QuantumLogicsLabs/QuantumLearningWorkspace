"""
Pinecone vector store wrapper.

Free tier: Pinecone's Starter/serverless plan supports this use case
at no cost for typical student-project volumes — verify current limits
at https://www.pinecone.io/pricing/ since free-tier terms can change.
"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
from pinecone import Pinecone, ServerlessSpec

from embedding.config import settings


class PineconeVectorStore:
    def __init__(self, index_name: str = None, dimension: int = None):
        if not settings.pinecone_api_key:
            raise RuntimeError(
                "PINECONE_API_KEY is not set. Add it to your .env file "
                "(get a free key at https://www.pinecone.io/)."
            )

        self.index_name = index_name or settings.pinecone_index_name
        self.dimension = dimension or settings.embedding_dimension

        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        self._ensure_index()
        self.index = self._pc.Index(self.index_name)

    def _ensure_index(self):
        existing = [i["name"] for i in self._pc.list_indexes()]
        if self.index_name not in existing:
            self._pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric=settings.pinecone_metric,
                spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
            )

    def upsert(self, vectors: list):
        """
        vectors: list of dicts, each:
          {"id": str, "values": [float, ...], "metadata": {...}}
        """
        if not vectors:
            return
        self.index.upsert(vectors=vectors)

    def query(self, vector: list, top_k: int = 5, filter: dict = None) -> list:
        """Returns Pinecone's list of matches: [{id, score, metadata}, ...]"""
        result = self.index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter=filter,
        )
        return result.get("matches", [])

    def delete(self, ids: list):
        if ids:
            self.index.delete(ids=ids)

    def delete_by_filter(self, filter: dict):
        self.index.delete(filter=filter)

    def stats(self) -> dict:
        return self.index.describe_index_stats()
