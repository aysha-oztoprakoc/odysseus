import pytest
from src.rag_manager import RAGManager

def test_search_signature_accepts_owner(mocker):
    # Mock VectorRAG
    mock_vector_rag_class = mocker.patch('src.rag_manager.VectorRAG')
    mock_vector_rag = mock_vector_rag_class.return_value

    # Initialize RAGManager
    manager = RAGManager()

    # Test call with owner parameter
    manager.search("test query", k=3, owner="user1")

    # Verify that search was called on the underlying vector_rag with the correct parameters
    mock_vector_rag.search.assert_called_once_with("test query", 3, owner="user1")
