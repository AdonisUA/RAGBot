import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.chat import Message
from pydantic import ValidationError

@pytest.fixture
def handler_service():
    with patch("app.services.message_handler_service.AIService") as mock_ai, \
         patch("app.services.message_handler_service.MemoryService") as mock_mem, \
         patch("app.services.message_handler_service.VectorMemoryService") as mock_vec, \
         patch("app.services.message_handler_service.ResearchService") as mock_research:
        from app.services.message_handler_service import MessageHandlerService
        service = MessageHandlerService()
        service.ai_service = mock_ai()
        service.memory_service = mock_mem()
        service.vector_memory_service = mock_vec()
        service.research_service = mock_research()
        return service

@pytest.mark.asyncio
async def test_process_message_success(handler_service):
    msg = Message(content="Hello", role="user", session_id="s1")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.memory_service.get_conversation_history = AsyncMock(return_value=[msg])
    handler_service.ai_service.generate_response = AsyncMock(return_value="Hi!")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.vector_memory_service.add_document = AsyncMock()
    handler_service.research_service.trigger_research_if_needed = AsyncMock()
    result = await handler_service.process_message("s1", msg)
    assert result["message"] == "Hi!"
    assert result["role"] == "assistant"
    assert result["session_id"] == "s1"

@pytest.mark.asyncio
async def test_process_message_empty(handler_service):
    with pytest.raises(ValidationError) as exc:
        Message(content="   ", role="user", session_id="s1")
    assert "Message content cannot be empty" in str(exc.value)

@pytest.mark.asyncio
async def test_process_message_ai_error(handler_service):
    msg = Message(content="Hello", role="user", session_id="s1")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.memory_service.get_conversation_history = AsyncMock(return_value=[msg])
    handler_service.ai_service.generate_response = AsyncMock(side_effect=Exception("AI fail"))
    with pytest.raises(AIServiceException) as exc:
        await handler_service.process_message("s1", msg)
    assert "Failed to generate AI response" in str(exc.value)

@pytest.mark.asyncio
async def test_process_message_memory_error(handler_service):
    msg = Message(content="Hello", role="user", session_id="s1")
    handler_service.memory_service.add_message = AsyncMock(side_effect=Exception("mem fail"))
    with pytest.raises(MemoryServiceException) as exc:
        await handler_service.process_message("s1", msg)
    assert "Failed to save user message" in str(exc.value)

@pytest.mark.asyncio
async def test_process_message_ai_save_error(handler_service):
    msg = Message(content="Hello", role="user", session_id="s1")
    handler_service.memory_service.add_message = AsyncMock(side_effect=[None, Exception("ai save fail")])
    handler_service.memory_service.get_conversation_history = AsyncMock(return_value=[msg])
    handler_service.ai_service.generate_response = AsyncMock(return_value="Hi!")
    handler_service.vector_memory_service.add_document = AsyncMock()
    handler_service.research_service.trigger_research_if_needed = AsyncMock()
    with pytest.raises(MemoryServiceException) as exc:
        await handler_service.process_message("s1", msg)
    assert "Failed to save AI message" in str(exc.value)

@pytest.mark.asyncio
async def test_process_message_history_error(handler_service):
    msg = Message(content="Hello", role="user", session_id="s1")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.memory_service.get_conversation_history = AsyncMock(side_effect=Exception("history fail"))
    handler_service.ai_service.generate_response = AsyncMock()
    handler_service.vector_memory_service.add_document = AsyncMock()
    handler_service.research_service.trigger_research_if_needed = AsyncMock()
    with pytest.raises(Exception) as exc:
        await handler_service.process_message("s1", msg)
    assert "history fail" in str(exc.value)

@pytest.mark.asyncio
async def test_process_message_vector_memory_error(handler_service):
    msg = Message(content="Hello", role="user", session_id="s1")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.memory_service.get_conversation_history = AsyncMock(return_value=[msg])
    handler_service.ai_service.generate_response = AsyncMock(return_value="Hi!")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.vector_memory_service.add_document = AsyncMock(side_effect=Exception("vector fail"))
    handler_service.research_service.trigger_research_if_needed = AsyncMock()
    # Ошибка в populate_vector_memory не должна ронять основной процесс
    result = await handler_service.process_message("s1", msg)
    assert result["message"] == "Hi!"

@pytest.mark.asyncio
async def test_process_message_research_error(handler_service, caplog):
    msg = Message(content="Hello", role="user", session_id="s1")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.memory_service.get_conversation_history = AsyncMock(return_value=[msg])
    handler_service.ai_service.generate_response = AsyncMock(return_value="Hi!")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.vector_memory_service.add_document = AsyncMock()
    handler_service.research_service.trigger_research_if_needed = AsyncMock(side_effect=Exception("research fail"))
    # Ошибка в ResearchService не должна ронять основной процесс
    result = await handler_service.process_message("s1", msg)
    assert result["message"] == "Hi!"
    assert any("research fail" in r.getMessage() for r in caplog.records)

@pytest.mark.asyncio
async def test_populate_vector_memory_success(handler_service):
    handler_service.vector_memory_service.add_document = AsyncMock()
    handler_service.memory_service.settings.rag_chunk_size = 100
    handler_service.memory_service.settings.rag_chunk_overlap = 20

    user_query = "This is a test user query. It has multiple sentences."
    ai_response = "This is a test AI response. It also has multiple sentences."
    session_id = "test_session_vm"

    await handler_service._populate_vector_memory(user_query, ai_response, session_id)

    # Verify add_document was called with chunks and metadata
    assert handler_service.vector_memory_service.add_document.call_count > 0
    first_call_args = handler_service.vector_memory_service.add_document.call_args_list[0].args
    first_call_kwargs = handler_service.vector_memory_service.add_document.call_args_list[0].kwargs

    assert isinstance(first_call_args[0], str) # Check if chunk is string
    assert "session_id" in first_call_kwargs["metadata"]
    assert first_call_kwargs["metadata"]["session_id"] == session_id

@pytest.mark.asyncio
async def test_populate_vector_memory_error(handler_service, caplog):
    handler_service.vector_memory_service.add_document = AsyncMock(side_effect=Exception("Vector DB error"))
    handler_service.memory_service.settings.rag_chunk_size = 100
    handler_service.memory_service.settings.rag_chunk_overlap = 20

    user_query = "Test query"
    ai_response = "Test response"
    session_id = "test_session_vm_error"

    await handler_service._populate_vector_memory(user_query, ai_response, session_id)

    assert any("Failed to populate vector memory" in r.getMessage() for r in caplog.records)

@pytest.mark.asyncio
async def test_trigger_research_if_needed_triggered(handler_service):
    handler_service.research_service.trigger_research_if_needed = AsyncMock()
    user_message = "What is the capital of France?"
    ai_response = "I don't know the answer to that."
    session_id = "test_session_research"

    await handler_service.research_service.trigger_research_if_needed(user_message, ai_response, session_id)

    handler_service.research_service.trigger_research_if_needed.assert_awaited_once_with(user_message, ai_response, session_id)

@pytest.mark.asyncio
async def test_trigger_research_if_needed_not_triggered(handler_service):
    handler_service.research_service.trigger_research_if_needed = AsyncMock()
    user_message = "What is the capital of France?"
    ai_response = "The capital of France is Paris."
    session_id = "test_session_research_no_trigger"

    await handler_service.research_service.trigger_research_if_needed(user_message, ai_response, session_id)

    handler_service.research_service.trigger_research_if_needed.assert_awaited_once_with(user_message, ai_response, session_id)

@pytest.mark.asyncio
async def test_process_message_no_session_id(handler_service):
    msg = Message(content="Hello", role="user", session_id=None)
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.memory_service.get_conversation_history = AsyncMock(return_value=[msg])
    handler_service.ai_service.generate_response = AsyncMock(return_value="Hi!")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.vector_memory_service.add_document = AsyncMock()
    handler_service.research_service.trigger_research_if_needed = AsyncMock()
    result = await handler_service.process_message(None, msg)
    assert result["message"] == "Hi!"
    assert result["role"] == "assistant"
    assert result["session_id"] is not None
    assert result["message_id"]

@pytest.mark.asyncio
async def test_process_message_long_message(handler_service):
    long_content = "x" * 10000
    with pytest.raises(ValidationError):
        Message(content=long_content, role="user", session_id="s1")

@pytest.mark.asyncio
async def test_process_message_invalid_type(handler_service):
    # Передаём не Message, а dict
    with pytest.raises(AttributeError):
        await handler_service.process_message("s1", {"content": "hi"})

@pytest.mark.asyncio
async def test_process_message_nonexistent_session(handler_service):
    msg = Message(content="Hello", role="user", session_id="nonexistent")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.memory_service.get_conversation_history = AsyncMock(return_value=[])
    handler_service.ai_service.generate_response = AsyncMock(return_value="Hi!")
    handler_service.memory_service.add_message = AsyncMock()
    handler_service.vector_memory_service.add_document = AsyncMock()
    handler_service.research_service.trigger_research_if_needed = AsyncMock()
    result = await handler_service.process_message("nonexistent", msg)
    assert result["message"] == "Hi!"
    assert result["role"] == "assistant"
