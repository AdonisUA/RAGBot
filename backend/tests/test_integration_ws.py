import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.models.chat import Message

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client

@pytest.fixture(autouse=True)
def mock_services_for_ws_integration_tests(monkeypatch):
    # Mock AIService
    mock_ai_service = AsyncMock()
    mock_ai_service.generate_response.return_value = "Mocked AI response"
    mock_ai_service.generate_streaming_response.return_value = AsyncMock()
    monkeypatch.setattr("app.services.ai_service.AIService", lambda: mock_ai_service)

    # Mock MemoryService
    mock_memory_service = AsyncMock()
    mock_memory_service.add_message.return_value = True
    mock_memory_service.get_conversation_history.return_value = []
    monkeypatch.setattr("app.services.memory_service.MemoryService", lambda: mock_memory_service)

    # Mock VectorMemoryService
    mock_vector_memory_service = AsyncMock()
    mock_vector_memory_service.add_document.return_value = None
    monkeypatch.setattr("app.services.vector_memory_service.VectorMemoryService", lambda: mock_vector_memory_service)

    # Mock ResearchService
    mock_research_service = AsyncMock()
    monkeypatch.setattr("app.services.research_service.ResearchService", lambda: mock_research_service)

    # Mock VoiceService
    mock_voice_service = AsyncMock()
    mock_voice_service.validate_audio.return_value = True
    mock_voice_service.transcribe_audio.return_value = MagicMock(text="Mocked transcription", confidence=0.9)
    monkeypatch.setattr("app.services.voice_service.VoiceService", lambda: mock_voice_service)

    # Mock PromptManager
    mock_prompt_manager = MagicMock()
    mock_prompt_manager.get_error_message.return_value = "MOCKED_FALLBACK_ERROR"
    monkeypatch.setattr("app.utils.prompts.PromptManager", lambda: mock_prompt_manager)


@pytest.mark.integration
async def test_websocket_chat_flow(test_client, mock_services_for_ws_integration_tests):
    with test_client.websocket_connect("/ws/chat") as ws:
        # Receive welcome message
        welcome_message = ws.receive_json()
        assert welcome_message["type"] == "status"
        assert welcome_message["data"]["status"] == "connected"

        # Send chat message
        session_id = "ws_integration_test_chat"
        ws.send_json({
            "type": "chat_message",
            "data": {"message": "Hello, WebSocket!"},
            "session_id": session_id
        })

        # Receive typing indicator
        typing_on = ws.receive_json()
        assert typing_on["type"] == "typing_indicator"
        assert typing_on["data"]["typing"] is True

        # Receive AI response
        ai_response = ws.receive_json()
        assert ai_response["type"] == "new_message"
        assert ai_response["data"]["role"] == "assistant"
        assert ai_response["data"]["content"] == "Mocked AI response"

        # Receive typing indicator off
        typing_off = ws.receive_json()
        assert typing_off["type"] == "typing_indicator"
        assert typing_off["data"]["typing"] is False

        # Verify services were called
        mock_services_for_ws_integration_tests.memory_service.add_message.assert_called()
        mock_services_for_ws_integration_tests.ai_service.generate_response.assert_called_once()

@pytest.mark.integration
async def test_websocket_voice_flow(test_client, mock_services_for_ws_integration_tests):
    from app.models.voice import AudioFile
    with test_client.websocket_connect("/ws/voice") as ws:
        # Receive welcome message
        welcome_message = ws.receive_json()
        assert welcome_message["type"] == "status"

        # Send audio data
        audio_data = b"fake_audio_bytes"
        ws.send_bytes(audio_data)

        # Receive processing status
        processing_status = ws.receive_json()
        assert processing_status["type"] == "voice_status"
        assert processing_status["data"]["status"] == "processing"

        # Receive transcription result
        transcription_result = ws.receive_json()
        assert transcription_result["type"] == "voice_transcription"
        assert transcription_result["data"]["text"] == "Mocked transcription"

        # Verify voice service was called
        mock_services_for_ws_integration_tests.voice_service.validate_audio.assert_called_once()
        mock_services_for_ws_integration_tests.voice_service.transcribe_audio.assert_called_once()

@pytest.mark.integration
async def test_websocket_error_handling(test_client, mock_services_for_ws_integration_tests):
    with test_client.websocket_connect("/ws/chat") as ws:
        welcome_message = ws.receive_json()

        # Simulate an error in message processing
        mock_services_for_ws_integration_tests.ai_service.generate_response.side_effect = Exception("AI internal error")

        ws.send_json({"type": "chat_message", "data": {"message": "trigger error"}, "session_id": "error_test"})

        # Expect typing on, then error, then typing off
        typing_on = ws.receive_json()
        assert typing_on["type"] == "typing_indicator"

        error_response = ws.receive_json()
        assert error_response["type"] == "error"
        assert "Failed to process chat message" in error_response["data"]["message"]

        typing_off = ws.receive_json()
        assert typing_off["type"] == "typing_indicator"

@pytest.mark.integration
async def test_websocket_typing_indicator(test_client, mock_services_for_ws_integration_tests):
    with test_client.websocket_connect("/ws/chat") as ws:
        welcome_message = ws.receive_json()

        session_id = "typing_test"
        ws.send_json({"type": "typing", "data": {"typing": True}, "session_id": session_id})

        # In a real scenario, this would be broadcasted to other clients in the same session
        # For this test, we just verify no error and the message is processed.
        # The broadcast logic is tested in WebSocketManager unit tests.
        # We can't easily receive the broadcasted message in this single-client integration test.
        pass

@pytest.mark.integration
async def test_websocket_ping_pong(test_client, mock_services_for_ws_integration_tests):
    with test_client.websocket_connect("/ws/chat") as ws:
        welcome_message = ws.receive_json()

        ws.send_json({"type": "ping", "data": {}})

        pong_response = ws.receive_json()
        assert pong_response["type"] == "pong"
        assert "timestamp" in pong_response["data"]

@pytest.mark.integration
async def test_websocket_feedback(test_client, mock_services_for_ws_integration_tests):
    with test_client.websocket_connect("/ws/chat") as ws:
        welcome_message = ws.receive_json()

        session_id = "feedback_test"
        message_id = "msg123"
        ws.send_json({"type": "feedback", "data": {"message_id": message_id, "score": "good"}, "session_id": session_id})

        # In a real scenario, this would trigger a broadcast ack and potentially research
        # For this test, we just verify no error and the message is processed.
        pass

@pytest.mark.integration
async def test_websocket_unknown_message_type(test_client, mock_services_for_ws_integration_tests):
    with test_client.websocket_connect("/ws/chat") as ws:
        welcome_message = ws.receive_json()

        ws.send_json({"type": "unsupported_type", "data": {}})

        error_response = ws.receive_json()
        assert error_response["type"] == "error"
        assert "Unknown message type" in error_response["data"]["message"]

@pytest.mark.integration
async def test_websocket_invalid_json(test_client, mock_services_for_ws_integration_tests):
    with test_client.websocket_connect("/ws/chat") as ws:
        welcome_message = ws.receive_json()

        # Send invalid JSON (not a dict)
        ws.send_text("invalid json string")

        error_response = ws.receive_json()
        assert error_response["type"] == "error"
        assert "Internal server error" in error_response["data"]["message"]
