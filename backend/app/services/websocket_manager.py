"""
WebSocket Manager for real-time communication
Handles chat and voice WebSocket connections
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
import structlog
from fastapi import WebSocket, WebSocketDisconnect
from uuid import uuid4
from broadcaster import Broadcast

from app.models.chat import WebSocketMessage, Message
from app.models.voice import VoiceWebSocketMessage, AudioFile
from app.services.ai_service import AIService
from app.services.voice_service import VoiceService
from app.services.memory_service import MemoryService
from app.services.message_handler_service import MessageHandlerService

# Импорт для celery worker
try:
    from app.worker import research_and_learn
except ImportError:
    research_and_learn = None

logger = structlog.get_logger()

BROADCAST_CHANNEL = "chatbot_ws"

class WebSocketManager:
    """Manages WebSocket connections and message routing (масштабируемый через Redis Pub/Sub)"""

    def __init__(
        self,
        ai_service: AIService = AIService(),
        voice_service: VoiceService = VoiceService(),
        memory_service: MemoryService = MemoryService(),
        message_handler_service: MessageHandlerService = MessageHandlerService()
    ):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_sessions: Dict[str, str] = {}  # connection_id -> session_id
        self.ai_service = ai_service
        self.voice_service = voice_service
        self.memory_service = memory_service
        self.message_handler_service = message_handler_service
        self.broadcast = Broadcast("redis://localhost:6379")
        self._subscriber_task = None

    async def start(self):
        await self.broadcast.connect()
        self._subscriber_task = asyncio.create_task(self._listen_pubsub())

    async def stop(self):
        if self._subscriber_task:
            self._subscriber_task.cancel()
        await self.broadcast.disconnect()

    async def _listen_pubsub(self):
        async with self.broadcast.subscribe(channel=BROADCAST_CHANNEL) as subscriber:
            async for event in subscriber:
                await self._handle_pubsub_event(event.message)

    async def _handle_pubsub_event(self, message: str):
        # message: JSON string {"session_id":..., "data":...}
        try:
            msg = json.loads(message)
            session_id = msg.get("session_id")
            data = msg.get("data")
            # Broadcast to all local clients in this session
            for conn_id, sess_id in self.connection_sessions.items():
                if sess_id == session_id and conn_id in self.active_connections:
                    await self.send_message(conn_id, data)
        except Exception as e:
            logger.error("Failed to handle pubsub event", error=str(e), raw=message)

    async def connect(self, websocket: WebSocket) -> str:
        """Accept WebSocket connection and return connection ID"""

        await websocket.accept()
        connection_id = str(uuid4())
        self.active_connections[connection_id] = websocket

        logger.info("WebSocket connected", connection_id=connection_id)

        # Send welcome message
        await self.send_message(connection_id, {
            "type": "status",
            "data": {
                "status": "connected",
                "connection_id": connection_id,
                "message": "WebSocket connection established"
            }
        })

        return connection_id

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""

        connection_id = None
        for conn_id, conn in self.active_connections.items():
            if conn == websocket:
                connection_id = conn_id
                break

        if connection_id:
            del self.active_connections[connection_id]
            if connection_id in self.connection_sessions:
                del self.connection_sessions[connection_id]

            logger.info("WebSocket disconnected", connection_id=connection_id)

    async def send_message(self, connection_id: str, data: Dict[str, Any]):
        """Send message to specific local connection"""
        if connection_id not in self.active_connections:
            logger.warning("Connection not found", connection_id=connection_id)
            return
        websocket = self.active_connections[connection_id]
        try:
            message = WebSocketMessage(
                type=data["type"],
                data=data["data"],
                session_id=self.connection_sessions.get(connection_id)
            )
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error("Failed to send WebSocket message", connection_id=connection_id, error=str(e))
            self.disconnect(websocket)

    async def broadcast_message(self, data: Dict[str, Any], session_id: Optional[str] = None):
        """Broadcast message to all connections in session (через Redis Pub/Sub)"""
        if not session_id:
            # Если нет session_id — отправить всем (например, system broadcast)
            for conn_id in list(self.active_connections.keys()):
                await self.send_message(conn_id, data)
            await self.broadcast.publish(channel=BROADCAST_CHANNEL, message=json.dumps({"session_id": None, "data": data}))
        else:
            # Публикуем в Redis, все инстансы доставят своим клиентам
            await self.broadcast.publish(channel=BROADCAST_CHANNEL, message=json.dumps({"session_id": session_id, "data": data}))

    async def handle_message(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""

        connection_id = self._get_connection_id(websocket)
        if not connection_id:
            await self.send_error(websocket, "Connection not found")
            return

        try:
            message_type = data.get("type")
            message_data = data.get("data", {})
            session_id = data.get("session_id")

            # Update session mapping
            if session_id:
                self.connection_sessions[connection_id] = session_id

            logger.info("WebSocket message received",
                       connection_id=connection_id,
                       type=message_type,
                       session_id=session_id)

            # Route message based on type
            if message_type == "chat_message":
                await self._handle_chat_message(connection_id, message_data, session_id)
            elif message_type == "typing":
                await self._handle_typing_indicator(connection_id, message_data, session_id)
            elif message_type == "ping":
                await self._handle_ping(connection_id)
            elif message_type == "feedback":
                await self._handle_feedback(connection_id, message_data, session_id)
            else:
                await self.send_message(connection_id, {
                    "type": "error",
                    "data": {"message": f"Unknown message type: {message_type}"}
                })

        except ChatBotException as e:
            logger.error("ChatBot exception in WebSocket handler",
                        exception_type=type(e).__name__,
                        message=e.message,
                        code=e.code,
                        details=e.details,
                        connection_id=connection_id)
            await self.send_message(connection_id, {
                "type": "error",
                "data": {"message": e.message}
            })
        except Exception as e:
            logger.error("Unhandled exception in WebSocket handler",
                        connection_id=connection_id,
                        error=str(e),
                        exc_info=True)
            await self.send_message(connection_id, {
                "type": "error",
                "data": {"message": "Internal server error"}
            })

    async def _handle_chat_message(
        self,
        connection_id: str,
        data: Dict[str, Any],
        session_id: Optional[str]
    ):
        """Handle chat message (масштабируемый, broadcast через Redis)"""
        from app.models.chat import Message
        user_msg = Message(content=data.get("message", ""), role="user", session_id=session_id)
        # Отправляем индикатор печати всем в сессии
        await self.broadcast_message({
            "type": "typing_indicator",
            "data": {"typing": True}
        }, session_id)
        try:
            result = await self.message_handler_service.process_message(session_id, user_msg)
            # Отправляем финальный ответ всем в сессии
            await self.broadcast_message({
                "type": "new_message",
                "data": {
                    "message_id": result["message_id"],
                    "session_id": result["session_id"],
                    "role": "assistant",
                    "content": result["message"]
                }
            }, session_id)
        except Exception as e:
            logger.error("Error in _handle_chat_message", error=str(e), exc_info=True)
            await self.broadcast_message({
                "type": "error",
                "data": {"message": "Failed to process chat message due to an internal error."}
            }, session_id)
        finally:
            await self.broadcast_message({
                "type": "typing_indicator",
                "data": {"typing": False}
            }, session_id)

    async def _handle_typing_indicator(
        self,
        connection_id: str,
        data: Dict[str, Any],
        session_id: Optional[str]
    ):
        """Handle typing indicator (масштабируемый)"""
        if session_id:
            await self.broadcast_message({
                "type": "typing",
                "data": {
                    "typing": data.get("typing", False),
                    "user_id": connection_id
                }
            }, session_id)

    async def _handle_ping(self, connection_id: str):
        """Handle ping message"""

        await self.send_message(connection_id, {
            "type": "pong",
            "data": {"timestamp": asyncio.get_event_loop().time()}
        })

    async def handle_voice_data(self, websocket: WebSocket, audio_data: bytes):
        """Handle voice data from WebSocket"""

        connection_id = self._get_connection_id(websocket)
        if not connection_id:
            await self.send_error(websocket, "Connection not found")
            return

        try:
            # Create audio file metadata
            audio_file = AudioFile(
                filename=f"voice_{connection_id}.wav",
                content_type="audio/wav",
                size_bytes=len(audio_data)
            )

            # Validate audio
            if not await self.voice_service.validate_audio(audio_data, audio_file.content_type):
                await self.send_message(connection_id, {
                    "type": "error",
                    "data": {"message": "Invalid audio data"}
                })
                return

            # Send processing status
            await self.send_message(connection_id, {
                "type": "voice_status",
                "data": {
                    "status": "processing",
                    "audio_id": audio_file.id
                }
            })

            # Transcribe audio
            transcription = await self.voice_service.transcribe_audio(
                audio_data,
                audio_file
            )

            # Send transcription result
            await self.send_message(connection_id, {
                "type": "voice_transcription",
                "data": {
                    "text": transcription.text,
                    "confidence": transcription.confidence,
                    "audio_id": audio_file.id
                }
            })

            # Auto-send to chat if enabled
            session_id = self.connection_sessions.get(connection_id)
            if session_id and transcription.text:
                await self._handle_chat_message(
                    connection_id,
                    {"message": transcription.text},
                    session_id
                )

        except Exception as e:
            logger.error("Error processing voice data",
                        connection_id=connection_id,
                        error=str(e))
            await self.send_message(connection_id, {
                "type": "error",
                "data": {"message": "Failed to process voice data"}
            })

    async def send_error(self, websocket: WebSocket, message: str):
        """Send error message to WebSocket"""

        try:
            error_msg = WebSocketMessage(
                type="error",
                data={"message": message}
            )
            await websocket.send_text(error_msg.model_dump_json())

        except Exception as e:
            logger.error("Failed to send error message", error=str(e))

    def _get_connection_id(self, websocket: WebSocket) -> Optional[str]:
        """Get connection ID for WebSocket"""

        for conn_id, conn in self.active_connections.items():
            if conn == websocket:
                return conn_id
        return None

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""

        return {
            "total_connections": len(self.active_connections),
            "active_sessions": len(set(self.connection_sessions.values())),
            "connections_by_session": {
                session_id: sum(1 for s in self.connection_sessions.values() if s == session_id)
                for session_id in set(self.connection_sessions.values())
            }
        }

    async def _handle_feedback(self, connection_id: str, data: Dict[str, Any], session_id: Optional[str]):
        """Handle feedback from user (like/dislike, масштабируемый)"""
        message_id = data.get("message_id")
        score = data.get("score")
        logger.info(
            "User feedback received",
            connection_id=connection_id,
            session_id=session_id,
            message_id=message_id,
            score=score
        )
        # Если дизлайк — вызвать research_and_learn
        if score == 'bad' and research_and_learn is not None:
            logger.info("Triggering research_and_learn Celery task due to negative feedback", message_id=message_id, session_id=session_id)
            research_and_learn.delay(f"feedback_bad_message_id:{message_id}")
        # Broadcast feedback ack всем в сессии
        await self.broadcast_message({
            "type": "feedback_ack",
            "data": {"message_id": message_id, "score": score}
        }, session_id)
