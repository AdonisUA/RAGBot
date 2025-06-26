"""
Memory Service for conversation storage
Handles JSON and Redis storage backends
- Redis backend теперь использует атомарные RPUSH/LTRIM/EXPIRE для истории сообщений.
- VectorMemoryService теперь всегда использует HTTP-клиент для ChromaDB.
"""

import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import structlog
import aiofiles
from pathlib import Path

from app.core.config import get_settings
from app.models.chat import Conversation, Message, ConversationSummary

logger = structlog.get_logger()


class MemoryService:
    """Conversation memory management service"""

    def __init__(self):
        self.settings = get_settings()
        self.storage_backend = None

        if self.settings.memory_type == "redis":
            self._init_redis_backend()
        else:
            self._init_json_backend()

    def _init_json_backend(self):
        """Initialize JSON file storage backend"""
        self.storage_backend = JSONStorageBackend(self.settings)
        logger.info("Initialized JSON storage backend")

    def _init_redis_backend(self):
        """Initialize Redis storage backend"""
        try:
            self.storage_backend = RedisStorageBackend(self.settings)
            logger.info("Initialized Redis storage backend")
        except Exception as e:
            logger.warning("Redis initialization failed, falling back to JSON", error=str(e))
            self._init_json_backend()

    async def save_conversation(self, conversation: Conversation) -> bool:
        """Save conversation to storage"""

        try:
            await self.storage_backend.save_conversation(conversation)
            logger.info("Conversation saved",
                       session_id=conversation.session_id,
                       message_count=conversation.message_count)
            return True

        except Exception as e:
            logger.error("Failed to save conversation",
                         session_id=conversation.session_id,
                         error=str(e))
            return False

    async def load_conversation(self, session_id: str) -> Optional[Conversation]:
        """Load conversation from storage"""

        try:
            conversation = await self.storage_backend.load_conversation(session_id)
            if conversation:
                logger.info("Conversation loaded",
                           session_id=session_id,
                           message_count=conversation.message_count)
            return conversation

        except Exception as e:
            logger.error("Failed to load conversation",
                         session_id=session_id,
                         error=str(e))
            return None

    async def add_message(self, session_id: str, message: Message) -> bool:
        """Add message to existing conversation"""
        try:
            if isinstance(self.storage_backend, RedisStorageBackend):
                await self.storage_backend.add_message(session_id, message)
                logger.info("Message added (atomic Redis)", session_id=session_id)
                return True
            # JSON fallback: This approach reloads and rewrites the entire conversation file.
            # For very long conversations, this can be inefficient. Redis is recommended for scalable message handling.
            conversation = await self.load_conversation(session_id)
            if not conversation:
                conversation = Conversation(session_id=session_id)
            conversation.add_message(message)
            if len(conversation.messages) > self.settings.max_history_messages:
                conversation.messages = conversation.messages[-self.settings.max_history_messages:]
            return await self.save_conversation(conversation)
        except Exception as e:
            logger.error("Failed to add message", session_id=session_id, error=str(e))
            return False

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """Get conversation history with pagination"""

        conversation = await self.load_conversation(session_id)
        if not conversation:
            return []

        messages = conversation.messages
        start_idx = max(0, len(messages) - offset - limit)
        end_idx = len(messages) - offset if offset > 0 else len(messages)

        return messages[start_idx:end_idx]

    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[ConversationSummary]:
        """List all conversations with summaries"""

        try:
            return await self.storage_backend.list_conversations(limit, offset)
        except Exception as e:
            logger.error("Failed to list conversations", error=str(e))
            return []

    async def delete_conversation(self, session_id: str) -> bool:
        """Delete conversation"""

        try:
            await self.storage_backend.delete_conversation(session_id)
            logger.info("Conversation deleted", session_id=session_id)
            return True

        except Exception as e:
            logger.error("Failed to delete conversation",
                         session_id=session_id,
                         error=str(e))
            return False

    async def cleanup_old_conversations(self, max_age_days: int = 30) -> int:
        """Cleanup old conversations"""

        try:
            deleted_count = await self.storage_backend.cleanup_old_conversations(max_age_days)
            logger.info("Cleaned up old conversations", deleted_count=deleted_count)
            return deleted_count

        except Exception as e:
            logger.error("Failed to cleanup conversations", error=str(e))
            return 0

    async def clear_all_conversations(self) -> int:
        """Clear all conversations from storage"""
        try:
            deleted_count = await self.storage_backend.clear_all_conversations()
            logger.info("Cleared all conversations", deleted_count=deleted_count)
            return deleted_count
        except Exception as e:
            logger.error("Failed to clear all conversations", error=str(e))
            return 0

    async def export_conversation(
        self,
        session_id: str,
        format: str = "json"
    ) -> Optional[str]:
        """Export conversation in specified format"""

        conversation = await self.load_conversation(session_id)
        if not conversation:
            return None

        if format == "json":
            return conversation.model_dump_json(indent=2)
        elif format == "txt":
            return self._export_as_text(conversation)
        elif format == "markdown":
            return self._export_as_markdown(conversation)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_as_text(self, conversation: Conversation) -> str:
        """Export conversation as plain text"""

        lines = [
            f"Conversation: {conversation.session_id}",
            f"Created: {conversation.created_at}",
            f"Messages: {conversation.message_count}",
            "-" * 50
        ]

        for message in conversation.messages:
            timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{timestamp}] {message.role.upper()}: {message.content}")

        return "\n".join(lines)

    def _export_as_markdown(self, conversation: Conversation) -> str:
        """Export conversation as markdown"""

        lines = [
            f"# Conversation {conversation.session_id}",
            f"**Created:** {conversation.created_at}",
            f"**Messages:** {conversation.message_count}",
            ""
        ]

        for message in conversation.messages:
            timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            role_emoji = "🧑" if message.role == "user" else "🤖"
            lines.append(f"## {role_emoji} {message.role.title()} - {timestamp}")
            lines.append(f"{message.content}")
            lines.append("")

        return "\n".join(lines)

    async def health_check(self) -> dict:
        """Check health of the current storage backend (JSON/Redis)"""
        if hasattr(self.storage_backend, 'health_check'):
            return await self.storage_backend.health_check()
        return {"status": "unknown", "storage_type": str(type(self.storage_backend))}


import aioredis
from typing import List, Optional
from datetime import datetime
import json

class RedisStorageBackend:
    """Redis storage backend (atomic RPUSH/LTRIM/EXPIRE for message history, efficient for chat logs)"""

    def __init__(self, settings):
        self.settings = settings
        self.redis = aioredis.from_url(self.settings.redis_url, decode_responses=True)
        self.max_history = self.settings.max_history_messages
        self.ttl = getattr(self.settings, 'redis_ttl', 86400)

    async def add_message(self, session_id: str, message: Message):
        key_messages = f"conversation:{session_id}:messages"
        key_meta = f"conversation:{session_id}:meta"
        key_sorted_set = "conversations_by_updated_at"
        try:
            pipe = self.redis.pipeline()
            pipe.rpush(key_messages, message.model_dump_json())
            pipe.ltrim(key_messages, -self.max_history, -1)
            pipe.expire(key_messages, self.ttl)

            now = datetime.utcnow()
            last_message_preview = message.content[:100] # Take first 100 chars of the new message

            pipe.hset(key_meta, mapping={
                "session_id": session_id,
                "updated_at": now.isoformat(),
                "last_message_preview": last_message_preview
            })
            pipe.expire(key_meta, self.ttl)

            # Add/Update session_id in sorted set with current timestamp as score
            pipe.zadd(key_sorted_set, {session_id: now.timestamp()})

            await pipe.execute()
        except Exception as e:
            logger = structlog.get_logger()
            logger.error("Redis add_message failed", error=str(e))
            raise

    async def save_conversation(self, conversation: Conversation):
        key_messages = f"conversation:{conversation.session_id}:messages"
        key_meta = f"conversation:{conversation.session_id}:meta"
        try:
            # Use WATCH for optimistic locking to prevent race conditions
            async with self.redis.pipeline() as pipe:
                while True:
                    try:
                        await pipe.watch(key_meta)
                        # Load current message count for increment
                        current_meta = await pipe.hgetall(key_meta)
                        current_count = int(current_meta.get("message_count", "0")) if current_meta else 0

                        pipe.multi()
                        pipe.delete(key_messages)
                        for message in conversation.messages:
                            pipe.rpush(key_messages, message.model_dump_json())
                        # Save metadata as a hash with updated message count
                        meta = {
                            "session_id": conversation.session_id,
                            "title": conversation.title or "",
                            "created_at": conversation.created_at.isoformat(),
                            "updated_at": conversation.updated_at.isoformat(),
                            "message_count": str(len(conversation.messages))
                        }
                        pipe.hset(key_meta, mapping=meta)
                        # Add/Update session_id in sorted set with current timestamp as score
                        pipe.zadd("conversations_by_updated_at", {conversation.session_id: conversation.updated_at.timestamp()})
                        await pipe.execute()
                        break
                    except Exception as watch_error:
                        # Retry if WATCH error occurs
                        continue
        except Exception as e:
            logger = structlog.get_logger()
            logger.error("Redis save_conversation failed, falling back to JSON", error=str(e))
            json_backend = JSONStorageBackend(self.settings)
            await json_backend.save_conversation(conversation)

    async def load_conversation(self, session_id: str) -> Optional[Conversation]:
        key_messages = f"conversation:{session_id}:messages"
        key_meta = f"conversation:{session_id}:meta"
        try:
            messages_data = await self.redis.lrange(key_messages, 0, -1)
            if not messages_data:
                return None
            messages = [Message.parse_raw(m) for m in messages_data]
            meta = await self.redis.hgetall(key_meta)
            if not meta:
                return None
            conversation = Conversation(
                session_id=meta.get("session_id", session_id),
                title=meta.get("title", ""),
                created_at=datetime.fromisoformat(meta.get("created_at")) if meta.get("created_at") else datetime.utcnow(),
                updated_at=datetime.fromisoformat(meta.get("updated_at")) if meta.get("updated_at") else datetime.utcnow(),
                messages=messages
            )
            return conversation
        except Exception as e:
            logger = structlog.get_logger()
            logger.error("Redis load_conversation failed", error=str(e))
            return None

    async def list_conversations(self, limit: int, offset: int) -> List[ConversationSummary]:
        try:
            # Use ZREVRANGE to get session_ids from the sorted set (newest first)
            # This is efficient for pagination
            session_ids = await self.redis.zrevrange("conversations_by_updated_at", offset, offset + limit - 1)
            
            summaries = []
            for session_id in session_ids:
                key_meta = f"conversation:{session_id}:meta"
                meta = await self.redis.hgetall(key_meta)
                if meta:
                    summary = ConversationSummary(
                        session_id=session_id,
                        title=meta.get("title", ""),
                        message_count=int(meta.get("message_count", "0")),
                        created_at=datetime.fromisoformat(meta.get("created_at")) if meta.get("created_at") else datetime.utcnow(),
                        updated_at=datetime.fromisoformat(meta.get("updated_at")) if meta.get("updated_at") else datetime.utcnow(),
                        last_message_preview=meta.get("last_message_preview")
                    )
                    summaries.append(summary)
            return summaries
        except Exception as e:
            logger = structlog.get_logger()
            logger.error("Redis list_conversations failed, falling back to JSON", error=str(e))
            json_backend = JSONStorageBackend(self.settings)
            return await json_backend.list_conversations(limit, offset)

    async def delete_conversation(self, session_id: str):
        key_messages = f"conversation:{session_id}:messages"
        key_meta = f"conversation:{session_id}:meta"
        try:
            await self.redis.delete(key_messages, key_meta)
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Redis delete_conversation failed, falling back to JSON", error=str(e))
            json_backend = JSONStorageBackend(self.settings)
            await json_backend.delete_conversation(session_id)

    async def cleanup_old_conversations(self, max_age_days: int) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        cutoff_timestamp = cutoff_date.timestamp()
        deleted_count = 0
        try:
            # Get session_ids from the sorted set that are older than cutoff_timestamp
            old_session_ids = await self.redis.zrangebyscore("conversations_by_updated_at", 0, cutoff_timestamp)
            
            for session_id in old_session_ids:
                # Delete conversation data
                key_messages = f"conversation:{session_id}:messages"
                key_meta = f"conversation:{session_id}:meta"
                await self.redis.delete(key_messages, key_meta)
                # Remove from sorted set
                await self.redis.zrem("conversations_by_updated_at", session_id)
                deleted_count += 1
            return deleted_count
        except Exception as e:
            logger = structlog.get_logger()
            logger.error("Redis cleanup_old_conversations failed, falling back to JSON", error=str(e))
            json_backend = JSONStorageBackend(self.settings)
            return await json_backend.cleanup_old_conversations(max_age_days)

    async def health_check(self) -> dict:
        try:
            pong = await self.redis.ping()
            return {"status": "healthy" if pong else "unhealthy", "storage_type": "redis"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "storage_type": "redis"}


class JSONStorageBackend:
    """JSON file storage backend for chat history (simple, not for production scale)"""
    def __init__(self, settings):
        self.settings = settings
        self.data_dir = Path(settings.json_data_dir) if hasattr(settings, 'json_data_dir') else Path("data/conversations")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_file(self, session_id: str) -> Path:
        return self.data_dir / f"{session_id}.json"

    async def save_conversation(self, conversation):
        file = self._get_file(conversation.session_id)
        async with aiofiles.open(file, "w") as f:
            await f.write(conversation.model_dump_json())

    async def load_conversation(self, session_id: str):
        file = self._get_file(session_id)
        if not file.exists():
            return None
        async with aiofiles.open(file, "r") as f:
            data = await f.read()
        from app.models.chat import Conversation
        return Conversation.parse_raw(data)

    async def list_conversations(self, limit: int, offset: int):
        from app.models.chat import ConversationSummary
        files = sorted(self.data_dir.glob("*.json"), reverse=True)[offset:offset+limit]
        summaries = []
        for file in files:
            async with aiofiles.open(file, "r") as f:
                data = await f.read()
            from app.models.chat import Conversation
            conv = Conversation.parse_raw(data)
            summaries.append(ConversationSummary(
                session_id=conv.session_id,
                title=conv.title or "",
                message_count=conv.message_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                last_message_preview=conv.messages[-1].content[:100] if conv.messages else None
            ))
        return summaries

    async def delete_conversation(self, session_id: str):
        file = self._get_file(session_id)
        if file.exists():
            file.unlink()

    async def cleanup_old_conversations(self, max_age_days: int):
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        deleted = 0
        for file in self.data_dir.glob("*.json"):
            if datetime.utcfromtimestamp(file.stat().st_mtime) < cutoff:
                file.unlink()
                deleted += 1
        return deleted

    async def health_check(self) -> dict:
        return {"status": "healthy", "storage_type": "json"}
