"""
Tests for the standalone utility functions — no database needed.
Run: pytest knowledge_graph/tests/test_utils.py
"""
import pytest

from knowledge_graph.app.utils.vectorizer import get_document_vector
from knowledge_graph.app.utils.similarity import cosine_similarity
from knowledge_graph.app.utils.topic_labeler import generate_label


def test_get_document_vector_averages_correctly():
    chunks = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    result = get_document_vector(chunks)
    assert abs(result[0] - 1 / 3) < 0.001
    assert abs(result[1] - 1 / 3) < 0.001
    assert abs(result[2] - 1 / 3) < 0.001


def test_get_document_vector_empty_raises():
    with pytest.raises(ValueError):
        get_document_vector([])


def test_cosine_similarity_identical_vectors():
    assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 0.001


def test_cosine_similarity_orthogonal_vectors():
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0]) - 0.0) < 0.001


def test_cosine_similarity_opposite_vectors():
    assert abs(cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 0.001


def test_cosine_similarity_zero_vector_raises():
    with pytest.raises(ValueError):
        cosine_similarity([0.0, 0.0], [1.0, 0.0])


def test_generate_label_finds_shared_terms():
    label = generate_label(
        "Backpropagation computes gradients in a neural network",
        "Gradient descent updates the neural network weights",
    )
    assert "shared terms" in label
    assert "neural" in label or "gradient" in label


def test_generate_label_no_overlap_falls_back():
    label = generate_label("Roman Empire history ancient", "Quantum physics particles")
    assert label == "related topics"
