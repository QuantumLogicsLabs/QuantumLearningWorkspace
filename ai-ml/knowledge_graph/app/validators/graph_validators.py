"""
Validation checks used before building or reading a graph.
"""


def validate_user_id(user_id: str) -> None:
    if not user_id or not isinstance(user_id, str):
        raise ValueError("A valid user_id is required")


def validate_documents_have_vectors(docs: dict) -> dict:
    """
    Filters out any document with no chunk vectors, so a document
    that failed to embed properly doesn't crash graph building.
    Returns the filtered dict; does not raise.
    """
    return {
        doc_id: data
        for doc_id, data in docs.items()
        if data.get("vectors")
    }
