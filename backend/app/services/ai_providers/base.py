"""
Base AI Provider interface
Abstract class for different AI providers
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.models.chat import Message, ChatSettings


class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def generate_response(
        self,
        message: str,
        context: List[Message],
        settings: Optional[ChatSettings] = None,
        stream: bool = False
    ) -> str:
        """Generate AI response for user message"""
        pass

    @abstractmethod
    async def generate_streaming_response(
        self,
        message: str,
        context: List[Message],
        settings: Optional[ChatSettings] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming AI response"""
        pass

    @abstractmethod
    async def validate_model(self, model_name: str) -> bool:
        """Validate if model is available"""
        pass

    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health"""
        pass

    @abstractmethod
    def build_messages(
        self,
        user_message: str,
        context: List[Message],
        settings: ChatSettings
    ) -> List[Dict[str, Any]]:
        """Build message list for provider API"""
        pass

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (default implementation)"""
        # Simple estimation: ~4 characters per token
        return len(text) // 4

    def get_provider_name(self) -> str:
        """Get provider name"""
        return self.__class__.__name__.replace("Provider", "").lower()
