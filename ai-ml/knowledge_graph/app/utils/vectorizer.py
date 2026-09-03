"""
Turns a document's many chunk vectors into a single vector
representing the whole document.
"""
import numpy as np


def get_document_vector(chunk_vectors: list) -> list:
    """
    Averages a list of chunk vectors into one document-level vector.

    chunk_vectors: list of vectors (list[float]), all the same length,
                   belonging to one document.

    Raises ValueError if no vectors are given, so callers can decide
    how to handle documents with no embedded chunks (e.g. skip them).
    """
    if not chunk_vectors:
        raise ValueError("get_document_vector() requires at least one chunk vector")

    return np.mean(np.array(chunk_vectors), axis=0).tolist()
