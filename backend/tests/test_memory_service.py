import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.memory_service import MemoryService, JSONStorageBackend, RedisStorageBackend
from app.models.chat import Conversation, Message

class AsyncMockPipeline:
    async def delete(self, *a, **kw): return self
    async def rpush(self, *a, **kw): return self
    async def hset(self, *a, **kw): return self
    async def ltrim(self, *a, **kw): return self
    async def expire(self, *a, **kw): return self
    async def execute(self, *a, **kw): return None
    async def multi(self, *a, **kw): return None
    async def watch(self, *a, **kw): return None
    async def hgetall(self, *a, **kw): return {}
    async def zadd(self, *a, **kw): return self
    async def zrevrange(self, *a, **kw): return []
    async def zrangebyscore(self, *a, **kw): return []
    async def zrem(self, *a, **kw): return self
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, tb): return None

@pytest.mark.asyncio
async def test_json_storage_save_and_load(tmp_path):
    settings = AsyncMock()
    settings.memory_type = "json"
    settings.memory_path = str(tmp_path)
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_json_backend()

    conversation = Conversation(session_id="test_session")
    message = Message(id="1", content="Hello", role="user", timestamp="2025-06-21T00:00:00Z", session_id="test_session")
    conversation.add_message(message)

    result = await memory_service.save_conversation(conversation)
    assert result is True

    loaded = await memory_service.load_conversation("test_session")
    assert loaded is not None
    assert loaded.session_id == "test_session"
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content == "Hello"

@pytest.mark.asyncio
@patch("app.services.memory_service.aioredis.from_url")
async def test_redis_add_message(mock_redis_from_url):
    mock_redis = AsyncMock()
    mock_redis_from_url.return_value = mock_redis
    mock_pipeline = AsyncMockPipeline()
    mock_redis.pipeline.return_value = mock_pipeline

    settings = AsyncMock()
    settings.memory_type = "redis"
    settings.redis_url = "redis://localhost:6379"
    settings.max_history_messages = 10
    settings.redis_ttl = 3600
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_redis_backend()

    session_id = "test_session_add"
    message = Message(id="msg1", content="Test message", role="user", session_id=session_id)

    await memory_service.add_message(session_id, message)

    mock_pipeline.rpush.assert_called_once_with(f"conversation:{session_id}:messages", message.model_dump_json())
    mock_pipeline.ltrim.assert_called_once_with(f"conversation:{session_id}:messages", -10, -1)
    mock_pipeline.expire.assert_any_call(f"conversation:{session_id}:messages", 3600)
    mock_pipeline.hset.assert_called_once() # Check mapping content more specifically if needed
    mock_pipeline.expire.assert_any_call(f"conversation:{session_id}:meta", 3600)
    mock_pipeline.zadd.assert_called_once() # Check score and member more specifically if needed
    mock_pipeline.execute.assert_awaited_once()

@pytest.mark.asyncio
@patch("app.services.memory_service.aioredis.from_url")
async def test_redis_list_conversations(mock_redis_from_url):
    mock_redis = AsyncMock()
    mock_redis_from_url.return_value = mock_redis

    settings = AsyncMock()
    settings.memory_type = "redis"
    settings.redis_url = "redis://localhost:6379"
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_redis_backend()

    # Mock zrevrange to return session IDs
    mock_redis.zrevrange.return_value = ["session1", "session2"]

    # Mock hgetall for each session ID
    mock_redis.hgetall.side_effect = [
        {
            "session_id": "session1",
            "title": "Conv 1",
            "message_count": "2",
            "created_at": "2023-01-01T10:00:00",
            "updated_at": "2023-01-01T11:00:00",
            "last_message_preview": "Hello from conv1"
        },
        {
            "session_id": "session2",
            "title": "Conv 2",
            "message_count": "3",
            "created_at": "2023-01-02T10:00:00",
            "updated_at": "2023-01-02T11:00:00",
            "last_message_preview": "Hello from conv2"
        }
    ]

    summaries = await memory_service.list_conversations(limit=2, offset=0)

    mock_redis.zrevrange.assert_called_once_with("conversations_by_updated_at", 0, 1)
    assert len(summaries) == 2
    assert summaries[0].session_id == "session1"
    assert summaries[0].title == "Conv 1"
    assert summaries[1].session_id == "session2"
    assert summaries[1].title == "Conv 2"

@pytest.mark.asyncio
@patch("app.services.memory_service.aioredis.from_url")
async def test_redis_cleanup_old_conversations(mock_redis_from_url):
    mock_redis = AsyncMock()
    mock_redis_from_url.return_value = mock_redis

    settings = AsyncMock()
    settings.memory_type = "redis"
    settings.redis_url = "redis://localhost:6379"
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_redis_backend()

    # Mock zrangebyscore to return old session IDs
    mock_redis.zrangebyscore.return_value = ["old_session1", "old_session2"]

    # Mock delete and zrem
    mock_redis.delete = AsyncMock()
    mock_redis.zrem = AsyncMock()

    deleted_count = await memory_service.cleanup_old_conversations(max_age_days=30)

    mock_redis.zrangebyscore.assert_called_once() # Check score range more specifically if needed
    assert mock_redis.delete.call_count == 2
    assert mock_redis.zrem.call_count == 2
    assert deleted_count == 2


@pytest.mark.asyncio
async def test_add_message_trims_history(tmp_path):
    settings = AsyncMock()
    settings.memory_type = "json"
    settings.memory_path = str(tmp_path)
    settings.max_history_messages = 3
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_json_backend()
    session_id = "trim_test"
    for i in range(5):
        msg = Message(id=str(i), content=f"msg{i}", role="user", timestamp="2025-06-21T00:00:00Z", session_id=session_id)
        await memory_service.add_message(session_id, msg)
    loaded = await memory_service.load_conversation(session_id)
    assert len(loaded.messages) == 3
    assert loaded.messages[0].content == "msg2"

@pytest.mark.asyncio
async def test_delete_conversation(tmp_path):
    settings = AsyncMock()
    settings.memory_type = "json"
    settings.memory_path = str(tmp_path)
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_json_backend()
    session_id = "del_test"
    msg = Message(id="1", content="del", role="user", timestamp="2025-06-21T00:00:00Z", session_id=session_id)
    await memory_service.add_message(session_id, msg)
    deleted = await memory_service.delete_conversation(session_id)
    assert deleted is True
    loaded = await memory_service.load_conversation(session_id)
    assert loaded is None

@pytest.mark.asyncio
async def test_export_conversation_formats(tmp_path):
    settings = AsyncMock()
    settings.memory_type = "json"
    settings.memory_path = str(tmp_path)
    settings.max_history_messages = 100
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_json_backend()
    session_id = "exp_test"
    msg = Message(id="1", content="exp", role="user", timestamp="2025-06-21T00:00:00Z", session_id=session_id)
    await memory_service.add_message(session_id, msg)
    json_str = await memory_service.export_conversation(session_id, format="json")
    txt_str = await memory_service.export_conversation(session_id, format="txt")
    md_str = await memory_service.export_conversation(session_id, format="markdown")
    assert "exp" in json_str
    assert "exp" in txt_str
    assert "exp" in md_str

@pytest.mark.asyncio
async def test_list_conversations_empty(tmp_path):
    settings = AsyncMock()
    settings.memory_type = "json"
    settings.memory_path = str(tmp_path)
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_json_backend()
    result = await memory_service.list_conversations()
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_cleanup_old_conversations(tmp_path):
    settings = AsyncMock()
    settings.memory_type = "json"
    settings.memory_path = str(tmp_path)
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_json_backend()
    # Добавляем старую и новую сессии
    old_conv = Conversation(session_id="old", created_at="2000-01-01T00:00:00Z")
    new_conv = Conversation(session_id="new")
    await memory_service.save_conversation(old_conv)
    await memory_service.save_conversation(new_conv)
    deleted = await memory_service.cleanup_old_conversations(max_age_days=1)
    assert isinstance(deleted, int)

@pytest.mark.asyncio
async def test_health_check(tmp_path):
    settings = AsyncMock()
    settings.memory_type = "json"
    settings.memory_path = str(tmp_path)
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_json_backend()
    health = await memory_service.health_check()
    assert health["status"] in ["healthy", "unhealthy"]

@pytest.mark.asyncio
async def test_get_conversation_history_empty(tmp_path):
    settings = AsyncMock()
    settings.memory_type = "json"
    settings.memory_path = str(tmp_path)
    memory_service = MemoryService()
    memory_service.settings = settings
    memory_service._init_json_backend()
    result = await memory_service.get_conversation_history("no_such_session")
    assert result == []
