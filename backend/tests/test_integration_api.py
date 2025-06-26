import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.models.chat import Message, Conversation
from datetime import datetime, timedelta

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client

@pytest.fixture(autouse=True)
def mock_services_for_integration_tests(monkeypatch):
    # Mock AIService
    mock_ai_service = AsyncMock()
    mock_ai_service.generate_response.return_value = "Mocked AI response"
    mock_ai_service.generate_streaming_response.return_value = AsyncMock()
    mock_ai_service.get_provider_info.return_value = {"current_provider": "openai", "available_providers": ["openai", "gemini"]}
    mock_ai_service.switch_provider.return_value = True
    mock_ai_service.get_available_models.return_value = ["gpt-3.5-turbo", "gpt-4"]
    mock_ai_service.get_all_available_models.return_value = {"openai": ["gpt-3.5-turbo"], "gemini": ["gemini-pro"]}
    monkeypatch.setattr("app.services.ai_service.AIService", lambda: mock_ai_service)

    # Mock MemoryService
    mock_memory_service = AsyncMock()
    mock_memory_service.add_message.return_value = True
    mock_memory_service.save_conversation.return_value = True
    mock_memory_service.load_conversation.return_value = None # Default to no conversation
    mock_memory_service.list_conversations.return_value = []
    mock_memory_service.delete_conversation.return_value = True
    mock_memory_service.cleanup_old_conversations.return_value = 0
    mock_memory_service.export_conversation.return_value = "exported data"
    monkeypatch.setattr("app.services.memory_service.MemoryService", lambda: mock_memory_service)

    # Mock VectorMemoryService
    mock_vector_memory_service = AsyncMock()
    mock_vector_memory_service.query.return_value = []
    monkeypatch.setattr("app.services.vector_memory_service.VectorMemoryService", lambda: mock_vector_memory_service)

    # Mock ResearchService
    mock_research_service = AsyncMock()
    monkeypatch.setattr("app.services.research_service.ResearchService", lambda: mock_research_service)

    # Mock PromptManager
    mock_prompt_manager = MagicMock()
    mock_prompt_manager.get_error_message.return_value = "MOCKED_FALLBACK_ERROR"
    monkeypatch.setattr("app.utils.prompts.PromptManager", lambda: mock_prompt_manager)


@pytest.mark.integration
def test_chat_message_flow(test_client, mock_services_for_integration_tests):
    # Отправляем сообщение в чат (payload соответствует ChatRequest)
    payload = {
        "message": "Привет, бот!",
        "session_id": "integration_test_session"
    }
    response = test_client.post("/api/chat/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["session_id"] == "integration_test_session"
    assert data["response"] == "Mocked AI response"

    # Проверяем, что add_message был вызван для пользовательского сообщения
    mock_services_for_integration_tests.memory_service.add_message.assert_any_call(
        payload["session_id"],
        Message(content=payload["message"], role="user", session_id=payload["session_id"])
    )
    # Проверяем, что add_message был вызван для ответа AI
    mock_services_for_integration_tests.memory_service.add_message.assert_any_call(
        payload["session_id"],
        Message(content="Mocked AI response", role="assistant", session_id=payload["session_id"])
    )

@pytest.mark.integration
def test_get_chat_history(test_client, mock_services_for_integration_tests):
    session_id = "history_test_session"
    mock_conversation = Conversation(session_id=session_id)
    mock_conversation.add_message(Message(content="User msg 1", role="user", session_id=session_id))
    mock_conversation.add_message(Message(content="AI msg 1", role="assistant", session_id=session_id))
    mock_services_for_integration_tests.memory_service.load_conversation.return_value = mock_conversation

    response = test_client.get(f"/api/chat/history/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert len(data["messages"]) == 2
    assert data["messages"][0]["content"] == "User msg 1"
    assert data["messages"][1]["content"] == "AI msg 1"
    assert data["total_messages"] == 2

@pytest.mark.integration
def test_list_conversations(test_client, mock_services_for_integration_tests):
    mock_summaries = [
        {
            "session_id": "conv1",
            "title": "Conversation 1",
            "message_count": 5,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "last_message_preview": "Last message of conv1"
        },
        {
            "session_id": "conv2",
            "title": "Conversation 2",
            "message_count": 3,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "last_message_preview": "Last message of conv2"
        }
    ]
    mock_services_for_integration_tests.memory_service.list_conversations.return_value = mock_summaries

    response = test_client.get("/api/chat/conversations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["session_id"] == "conv1"
    assert data[1]["session_id"] == "conv2"

@pytest.mark.integration
def test_delete_conversation(test_client, mock_services_for_integration_tests):
    session_id = "delete_test_session"
    response = test_client.delete(f"/api/chat/conversation/{session_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Conversation deleted successfully"
    mock_services_for_integration_tests.memory_service.delete_conversation.assert_called_once_with(session_id)

@pytest.mark.integration
def test_export_conversation(test_client, mock_services_for_integration_tests):
    session_id = "export_test_session"
    mock_services_for_integration_tests.memory_service.export_conversation.return_value = "mocked export content"

    response = test_client.get(f"/api/chat/conversation/{session_id}/export?format=txt")
    assert response.status_code == 200
    assert response.text == "mocked export content"
    assert response.headers["content-type"] == "text/plain"
    assert "filename=conversation_export_test_session.txt" in response.headers["content-disposition"]
    mock_services_for_integration_tests.memory_service.export_conversation.assert_called_once_with(session_id, "txt")

@pytest.mark.integration
def test_cleanup_old_conversations(test_client, mock_services_for_integration_tests):
    mock_services_for_integration_tests.memory_service.cleanup_old_conversations.return_value = 5
    response = test_client.post("/api/chat/cleanup?max_age_days=7")
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 5
    mock_services_for_integration_tests.memory_service.cleanup_old_conversations.assert_called_once_with(7)

@pytest.mark.integration
def test_get_ai_providers(test_client, mock_services_for_integration_tests):
    response = test_client.get("/api/chat/providers")
    assert response.status_code == 200
    data = response.json()
    assert data["current_provider"] == "openai"
    assert "openai" in data["available_providers"]

@pytest.mark.integration
def test_switch_ai_provider(test_client, mock_services_for_integration_tests):
    response = test_client.post("/api/chat/providers/switch?provider=gemini")
    assert response.status_code == 200
    assert response.json()["message"] == "Switched to provider: gemini"
    mock_services_for_integration_tests.ai_service.switch_provider.assert_called_once_with("gemini")

@pytest.mark.integration
def test_get_available_models(test_client, mock_services_for_integration_tests):
    response = test_client.get("/api/chat/models")
    assert response.status_code == 200
    data = response.json()
    assert "openai" in data["providers"]
    assert "gemini" in data["providers"]
    assert "gpt-3.5-turbo" in data["providers"]["openai"]

@pytest.mark.integration
def test_get_available_models_specific_provider(test_client, mock_services_for_integration_tests):
    response = test_client.get("/api/chat/models?provider=openai")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert "gpt-3.5-turbo" in data["models"]
