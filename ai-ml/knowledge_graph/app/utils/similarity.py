"""
Cosine similarity between two vectors.
"""
import numpy as np


def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """
    Returns a score from -1 to 1. Closer to 1 means more related.

    Raises ValueError if either vector has zero magnitude (all zeros),
    since cosine similarity is undefined in that case.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        raise ValueError("cosine_similarity() received a zero-magnitude vector")

    return float(np.dot(a, b) / (norm_a * norm_b))
