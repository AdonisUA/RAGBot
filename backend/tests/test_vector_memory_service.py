import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.vector_memory_service import VectorMemoryService

@pytest.fixture
def vector_service(monkeypatch):
    # Mock get_settings to control settings
    mock_settings = MagicMock()
    mock_settings.chroma_api_url = "http://test-chroma:8000"
    mock_settings.chroma_collection_name = "test_collection"
    mock_settings.rag_embedding_model = "all-MiniLM-L6-v2"
    monkeypatch.setattr("app.services.vector_memory_service.get_settings", lambda: mock_settings)

    # Mock chromadb.Client and its methods
    mock_chroma_client = MagicMock()
    mock_chroma_client.get_or_create_collection.return_value = MagicMock()
    mock_chroma_client.list_collections.return_value = []
    monkeypatch.setattr("app.services.vector_memory_service.Client", MagicMock(return_value=mock_chroma_client))

    # Mock embedding_functions.SentenceTransformerEmbeddingFunction
    mock_embedding_function = MagicMock()
    monkeypatch.setattr("app.services.vector_memory_service.embedding_functions.SentenceTransformerEmbeddingFunction", MagicMock(return_value=mock_embedding_function))

    service = VectorMemoryService()
    service.client = mock_chroma_client
    service.collection = mock_chroma_client.get_or_create_collection.return_value
    service.embedding_function = mock_embedding_function # Store for assertion
    return service

@pytest.mark.asyncio
async def test_initialize_chroma_client_success(monkeypatch):
    mock_settings = MagicMock()
    mock_settings.chroma_api_url = "http://localhost:8000"
    monkeypatch.setattr("app.services.vector_memory_service.get_settings", lambda: mock_settings)
    
    mock_chroma_client_class = MagicMock()
    monkeypatch.setattr("app.services.vector_memory_service.Client", mock_chroma_client_class)

    service = VectorMemoryService()
    service._initialized = False # Force re-initialization for this test
    service.__init__() # Call init again to test client initialization

    mock_chroma_client_class.assert_called_once_with(MagicMock(
        chroma_api_impl="chromadb.api.fastapi.FastAPI",
        chroma_server_host="localhost",
        chroma_server_http_port=8000
    ))
    assert service.client == mock_chroma_client_class.return_value

@pytest.mark.asyncio
async def test_initialize_chroma_client_no_url(monkeypatch):
    mock_settings = MagicMock()
    mock_settings.chroma_api_url = None
    monkeypatch.setattr("app.services.vector_memory_service.get_settings", lambda: mock_settings)

    with pytest.raises(RuntimeError, match="chroma_api_url is required for ChromaDB HTTP client."):
        VectorMemoryService()

@pytest.mark.asyncio
async def test_get_or_create_collection(vector_service):
    vector_service.client.get_or_create_collection.reset_mock()
    vector_service.settings.chroma_collection_name = "new_collection"
    vector_service.settings.rag_embedding_model = "test-embedding-model"

    # Force re-initialization of collection for this test
    vector_service._get_or_create_collection()

    vector_service.client.get_or_create_collection.assert_called_once()
    args, kwargs = vector_service.client.get_or_create_collection.call_args
    assert kwargs["name"] == "new_collection"
    assert kwargs["embedding_function"] == vector_service.embedding_function
    vector_service.embedding_function.model_name == "test-embedding-model"

@pytest.mark.asyncio
async def test_add_document(vector_service):
    vector_service.collection.add = MagicMock()
    await vector_service.add_document("test text", {"meta": "data"}, doc_id="doc1")
    vector_service.collection.add.assert_called_once()
    args, kwargs = vector_service.collection.add.call_args
    assert "test text" in kwargs["documents"]
    assert kwargs["metadatas"][0]["meta"] == "data"
    assert kwargs["ids"][0] == "doc1"

@pytest.mark.asyncio
async def test_add_document_auto_id_no_metadata(vector_service):
    vector_service.collection.add = MagicMock()
    await vector_service.add_document("another text")
    vector_service.collection.add.assert_called_once()
    args, kwargs = vector_service.collection.add.call_args
    assert "another text" in kwargs["documents"]
    assert kwargs["metadatas"][0] == {}
    assert isinstance(kwargs["ids"][0], str) # Check if UUID string

@pytest.mark.asyncio
async def test_add_document_error(vector_service):
    vector_service.collection.add.side_effect = Exception("Chroma add error")
    with pytest.raises(Exception, match="Chroma add error"):
        await vector_service.add_document("text")

@pytest.mark.asyncio
async def test_query(vector_service):
    # Мокаем результат ChromaDB
    vector_service.collection.query.return_value = {
        "documents": [["doc text"]],
        "metadatas": [[{"meta": "data"}]],
        "distances": [[0.1]]
    }
    results = await vector_service.query("test query", top_k=1)
    vector_service.collection.query.assert_called_once()
    assert len(results) == 1
    assert results[0]["document"] == "doc text"
    assert results[0]["metadata"]["meta"] == "data"
    assert results[0]["distance"] == 0.1

@pytest.mark.asyncio
async def test_query_empty_results(vector_service):
    vector_service.collection.query.return_value = {
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]]
    }
    results = await vector_service.query("test query", top_k=1)
    vector_service.collection.query.assert_called_once()
    assert results == []

@pytest.mark.asyncio
async def test_query_error(vector_service):
    vector_service.collection.query.side_effect = Exception("Chroma query error")
    with pytest.raises(Exception, match="Chroma query error"):
        await vector_service.query("text")

@pytest.mark.asyncio
async def test_health_check(vector_service):
    mock_collection = MagicMock()
    mock_collection.name = "test_collection"
    vector_service.client.list_collections.return_value = [mock_collection]
    health = await vector_service.health_check()
    assert health["status"] == "healthy"
    assert health["collections"] == ["test_collection"]

@pytest.mark.asyncio
async def test_health_check_error(vector_service):
    vector_service.client.list_collections.side_effect = Exception("Chroma health error")
    health = await vector_service.health_check()
    assert health["status"] == "unhealthy"
    assert "Chroma health error" in health["error"]
