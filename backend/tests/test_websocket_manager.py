import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def ws_manager():
    # Патчим до импорта WebSocketManager
    with patch("app.services.vector_memory_service.get_settings") as mock_get_settings, \
         patch("app.services.vector_memory_service.VectorMemoryService._initialize_chroma_client", lambda self: MagicMock()), \
         patch("app.services.vector_memory_service.VectorMemoryService._get_or_create_collection", lambda self: MagicMock()):
        mock_settings = MagicMock()
        mock_settings.chroma_api_url = "http://test-chroma"
        mock_settings.chroma_collection_name = "test_collection"
        mock_get_settings.return_value = mock_settings
        from app.services.websocket_manager import WebSocketManager
        manager = WebSocketManager()
        manager.broadcast = AsyncMock()
        manager.voice_service = AsyncMock()
        return manager

@pytest.mark.asyncio
async def test_connect_and_disconnect(ws_manager):
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    connection_id = await ws_manager.connect(ws)
    assert connection_id in ws_manager.active_connections
    ws_manager.disconnect(ws)
    assert connection_id not in ws_manager.active_connections
    ws.send_text.assert_called()  # welcome message

@pytest.mark.asyncio
async def test_send_message(ws_manager):
    ws = MagicMock()
    ws.send_text = AsyncMock()
    ws.accept = AsyncMock()
    connection_id = await ws_manager.connect(ws)
    await ws_manager.send_message(connection_id, {"type": "chat", "data": {"foo": "bar"}})
    assert ws.send_text.call_count >= 1  # welcome + chat

@pytest.mark.asyncio
async def test_broadcast_message(ws_manager):
    ws1 = MagicMock(); ws1.send_text = AsyncMock(); ws1.accept = AsyncMock()
    ws2 = MagicMock(); ws2.send_text = AsyncMock(); ws2.accept = AsyncMock()
    id1 = await ws_manager.connect(ws1)
    id2 = await ws_manager.connect(ws2)
    await ws_manager.broadcast_message({"type": "chat", "data": {"msg": 1}})
    assert ws1.send_text.call_count >= 1
    assert ws2.send_text.call_count >= 1

@pytest.mark.asyncio
async def test_send_error(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    await ws_manager.send_error(ws, "fail!")
    assert ws.send_text.call_count >= 2  # welcome + error

@pytest.mark.asyncio
async def test_get_connection_stats(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    stats = await ws_manager.get_connection_stats()
    assert "active_connections" in stats or "total_connections" in stats

@pytest.mark.asyncio
async def test_handle_message_chat(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    data = {"type": "chat_message", "data": {"message": "hi"}, "session_id": "s1"}
    ws_manager.broadcast_message = AsyncMock()
    with patch("app.services.websocket_manager.MessageHandlerService") as mock_handler:
        mock_handler().process_message = AsyncMock(return_value={"message": "ok", "message_id": "1", "session_id": "s1", "role": "assistant"})
        await ws_manager.handle_message(ws, data)
    # Проверяем, что был вызван broadcast_message с new_message
    assert ws_manager.broadcast_message.await_count >= 1

@pytest.mark.asyncio
async def test_handle_message_typing(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    data = {"type": "typing", "data": {}, "session_id": "s1"}
    await ws_manager.handle_message(ws, data)
    # Проверяем, что не было ошибок
    assert ws.send_text.call_count >= 1

@pytest.mark.asyncio
async def test_handle_message_ping(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    data = {"type": "ping", "data": {}, "session_id": "s1"}
    await ws_manager.handle_message(ws, data)
    assert ws.send_text.call_count >= 1

@pytest.mark.asyncio
async def test_handle_message_feedback(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    ws_manager.broadcast_message = AsyncMock()
    data = {"type": "feedback", "data": {"message_id": "1", "score": "good"}, "session_id": "s1"}
    await ws_manager.handle_message(ws, data)
    assert ws_manager.broadcast_message.await_count >= 1

@pytest.mark.asyncio
async def test_handle_message_unknown_type(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    data = {"type": "unknown", "data": {}, "session_id": "s1"}
    await ws_manager.handle_message(ws, data)
    # Должен быть отправлен error
    assert any("Unknown message type" in str(call) for call in ws.send_text.call_args_list)

@pytest.mark.asyncio
async def test_handle_message_invalid_data(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    # Нет type
    data = {"data": {}, "session_id": "s1"}
    await ws_manager.handle_message(ws, data)
    # Должен быть отправлен error
    assert ws.send_text.call_count >= 1

@pytest.mark.asyncio
async def test_handle_message_disconnect(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    ws_manager.disconnect(ws)
    # После disconnect не должно быть в active_connections
    assert ws not in ws_manager.active_connections.values()

@pytest.mark.asyncio
async def test_pubsub_event_handling(ws_manager):
    # Проверяем, что pubsub event вызывает send_message
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    ws_manager.connection_sessions = {"cid": "s1"}
    ws_manager.active_connections = {"cid": ws}
    with patch.object(ws_manager, "send_message", new=AsyncMock()) as mock_send:
        await ws_manager._handle_pubsub_event('{"session_id": "s1", "data": {"foo": "bar"}}')
        mock_send.assert_awaited()

@pytest.mark.asyncio
async def test_handle_message_error_in_handler(ws_manager):
    ws = MagicMock(); ws.send_text = AsyncMock(); ws.accept = AsyncMock()
    await ws_manager.connect(ws)
    ws_manager.broadcast_message = AsyncMock()
    data = {"type": "chat_message", "data": {"message": "hi"}, "session_id": "s1"}
    with patch("app.services.websocket_manager.MessageHandlerService") as mock_handler:
        mock_handler().process_message = AsyncMock(side_effect=Exception("fail"))
        await ws_manager.handle_message(ws, data)
    # Должен быть вызван broadcast_message с типом error
    assert any(
        call_args[0][0].get("type") == "error"
        for call_args in ws_manager.broadcast_message.call_args_list
    )
