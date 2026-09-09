import pytest
from unittest.mock import MagicMock, patch
from embedding.chroma_store import store_chunks

def test_store_chunks_happy_path():
    """Task 4: Happy Path - Mock everything to avoid disk and AI model delays."""
    
    # 1. Provide a chunk that matches your Chunker.py output exactly
    mock_chunks = [{
        "text": "sample text",
        "chunk_index": 0
    }]

    # 2. We mock the Client and the Model
    # This prevents the code from touching C:\Dev\... and from loading AI weights
    with patch("embedding.chroma_store.chromadb.PersistentClient") as mock_client_class, \
         patch("embedding.chroma_store.get_embedding_model") as mock_get_model:
        
        # Setup the database mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_col = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_col
        
        # Setup the model mock
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_model.encode.return_value = [[0.1, 0.2]]

        # 3. Call the function
        result = store_chunks(mock_chunks, "user_1", "doc_1", "Test Title")

        # 4. Verify
        assert result == 1
        # Your code uses upsert, so we check that
        assert mock_col.upsert.called 
        
        # Verify the ID was created correctly: {doc_id}_chunk{index}
        args, kwargs = mock_col.upsert.call_args
        assert kwargs['ids'][0] == "doc_1_chunk0"

def test_store_chunks_empty_list():
    """Task 4: Edge Case - Empty list returns 0."""
    from embedding.chroma_store import store_chunks
    assert store_chunks([], "user", "doc", "title") == 0