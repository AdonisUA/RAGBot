"""
Data models package for AI ChatBot
"""

from pydantic import BaseModel
from datetime import datetime

class BaseAppModel(BaseModel):
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

from .chat import (
    Message,
    Conversation,
    ChatRequest,
    ChatResponse,
    ChatHistory,
    ConversationSummary,
    ChatSettings,
    WebSocketMessage,
    ErrorResponse
)

from .voice import (
    AudioFile,
    VoiceRequest,
    TranscriptionResult,
    VoiceResponse,
    VoiceSettings,
    AudioProcessingStatus,
    VoiceWebSocketMessage,
    AudioChunk,
    VoiceMetrics
)

__all__ = [
    "BaseAppModel",
    # Chat models
    "Message",
    "Conversation",
    "ChatRequest",
    "ChatResponse",
    "ChatHistory",
    "ConversationSummary",
    "ChatSettings",
    "WebSocketMessage",
    "ErrorResponse",

    # Voice models
    "AudioFile",
    "VoiceRequest",
    "TranscriptionResult",
    "VoiceResponse",
    "VoiceSettings",
    "AudioProcessingStatus",
    "VoiceWebSocketMessage",
    "AudioChunk",
    "VoiceMetrics"
]