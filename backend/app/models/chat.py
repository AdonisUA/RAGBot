"""
Chat data models for AI ChatBot
Pydantic models for request/response validation
"""

from pydantic import Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4, UUID
from app.models import BaseAppModel


class Message(BaseAppModel):
    """Individual chat message"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = Field(..., min_length=1, max_length=4000)
    role: Literal["user", "assistant", "system"] = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    session_id: Optional[str] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Validate message content"""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()


class Conversation(BaseAppModel):
    """Chat conversation container"""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    title: Optional[str] = None

    def add_message(self, message: Message) -> None:
        """Add message to conversation"""
        message.session_id = self.session_id
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def get_context(self, max_messages: int = 10) -> List[Message]:
        """Get recent messages for context"""
        return self.messages[-max_messages:] if self.messages else []

    @property
    def message_count(self) -> int:
        """Get total message count"""
        return len(self.messages)


class ChatRequest(BaseAppModel):
    """Chat message request"""
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    context_length: int = Field(50, ge=1, le=100) # Updated default and max
    stream: bool = Field(False)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        """Validate message content"""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class ChatResponse(BaseAppModel):
    """Chat message response"""
    response: str = Field(...)
    session_id: str = Field(...)
    message_id: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    usage: Optional[Dict[str, Any]] = None


class ChatHistory(BaseAppModel):
    """Chat history response"""
    session_id: str = Field(...)
    messages: List[Message] = Field(...)
    total_messages: int = Field(...)
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)
    has_more: bool = Field(False)


class ConversationSummary(BaseAppModel):
    """Conversation summary for listing"""
    session_id: str = Field(...)
    title: Optional[str] = None
    message_count: int = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    last_message_preview: Optional[str] = None


class ChatSettings(BaseAppModel):
    """Chat configuration settings"""
    model: str = Field("gpt-3.5-turbo")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(1000, ge=1, le=4000)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    system_prompt: Optional[str] = None
    context_window: int = Field(50, ge=1, le=100) # Updated default and max


class ErrorResponse(BaseAppModel):
    """Error response model"""
    error: str = Field(...)
    message: str = Field(...)
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Specific WebSocket data models
class ChatWebSocketData(BaseAppModel):
    content: str = Field(...)
    role: Literal["user", "assistant"] = Field(...)
    message_id: Optional[str] = None

class TypingWebSocketData(BaseAppModel):
    typing: bool = Field(...)
    user_id: Optional[str] = None

class StatusWebSocketData(BaseAppModel):
    status: str = Field(...)
    connection_id: Optional[str] = None
    message: Optional[str] = None

class ErrorWebSocketData(BaseAppModel):
    message: str = Field(...)
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class WebSocketMessage(BaseAppModel):
    """WebSocket message format"""
    type: Literal["chat_message", "typing", "error", "status", "new_message", "typing_indicator", "pong", "feedback"] = Field(...)
    data: Union[ChatWebSocketData, TypingWebSocketData, StatusWebSocketData, ErrorWebSocketData, Dict[str, Any]] = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


class ErrorResponse(BaseAppModel):
    """Error response model"""
    error: str = Field(...)
    message: str = Field(...)
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
