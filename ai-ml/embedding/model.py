"""
Embedding model wrapper.

Uses sentence-transformers (free, open-source, runs locally after the
model weights are downloaded once — no API key, no per-call cost).
"""

from functools import lru_cache
from sentence_transformers import SentenceTransformer

from embedding.config import settings


class EmbeddingModel:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model_name
        self._model = SentenceTransformer(self.model_name)

    def encode(self, texts, batch_size: int = 32) -> list:
        """
        texts: a single string or a list of strings.
        Returns a list of embedding vectors (list[float]).
        """
        single_input = isinstance(texts, str)
        if single_input:
            texts = [texts]

        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,  # cosine similarity works cleanly on normalized vectors
        )
        return vectors.tolist()

    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()


@lru_cache(maxsize=1)
def get_embedding_model() -> EmbeddingModel:
    """Singleton so the model is loaded into memory only once per process."""
    return EmbeddingModel()


if __name__ == "__main__":
    # quick manual test: python -m embedding.model
    model = get_embedding_model()
    vecs = model.encode(["Machine learning is a branch of artificial intelligence."])
    print(f"Model: {model.model_name}")
    print(f"Dimension: {model.dimension()}")
    print(f"First 5 values of vector: {vecs[0][:5]}")
