"""
Universal AI Service with multiple provider support
Handles chat completions and AI responses from different providers
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, AsyncGenerator, Type
import structlog

from app.core.config import get_settings
from app.models.chat import Message, ChatSettings
from app.utils.prompts import PromptManager
from app.services.ai_providers.openai_provider import OpenAIProvider
from app.services.ai_providers.gemini_provider import GeminiProvider
from app.services.vector_memory_service import VectorMemoryService # Import new service

logger = structlog.get_logger()

class AIService:
    """Universal AI service with multiple provider support"""

    # Фабрика провайдеров
    _providers: Dict[str, Type] = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type):
        from app.services.ai_providers.base import BaseAIProvider
        if not issubclass(provider_class, BaseAIProvider):
            raise TypeError("Provider must be a subclass of BaseAIProvider")
        cls._providers[name] = provider_class
        logger.info(f"AI Provider '{name}' registered.")

    def __init__(self):
        self.settings = get_settings()
        self.prompt_manager = PromptManager()
        self.vector_memory_service = VectorMemoryService()
        self._initialized_providers: Dict[str, Any] = {} # Store initialized provider instances
        self.current_provider = self.settings.ai_provider # Set initial current provider

    def get_provider(self, provider_name: Optional[str] = None):
        """Get AI provider instance (lazy initialization)"""

        provider_name = provider_name or self.current_provider

        if provider_name not in self._providers:
            raise ValueError(f"Provider '{provider_name}' not registered. Available: {list(self._providers.keys())}")

        if provider_name not in self._initialized_providers:
            provider_class = self._providers[provider_name]
            config = {}
            if hasattr(self.settings, f"{provider_name}_api_key"):
                config["api_key"] = getattr(self.settings, f"{provider_name}_api_key")
            if hasattr(self.settings, f"{provider_name}_model"):
                config["model"] = getattr(self.settings, f"{provider_name}_model")
            try:
                provider_instance = provider_class(config)
                self._initialized_providers[provider_name] = provider_instance
                logger.info(f"{provider_class.__name__} initialized as '{provider_name}'")
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider_name}", error=str(e))
                raise RuntimeError(f"Failed to initialize provider {provider_name}") from e

        return self._initialized_providers[provider_name]

    async def generate_response(
        self,
        message: str,
        context: List[Message],
        settings: Optional[ChatSettings] = None,
        stream: bool = False,
        provider: Optional[str] = None
    ) -> str:
        """Generate AI response for user message"""

        start_time = time.time()

        try:
            # Get provider
            ai_provider = self.get_provider(provider)
            provider_name = provider or self.current_provider

            # Use provided settings or defaults
            chat_settings = settings or ChatSettings()

            modified_context, rag_enabled = await self._get_rag_context_and_modify_messages(message, context)


            # Log request
            logger.info("AI request started",
                       provider=provider_name,
                       model=chat_settings.model,
                       message_length=len(message),
                       context_length=len(modified_context),
                       session_id=context[-1].session_id if context else None, # Assuming last message in context has session_id
                       user_message_preview=message[:50],
                       rag_enabled=bool(rag_context))

            # Generate response using provider
            response = await ai_provider.generate_response(
                message, modified_context, chat_settings, stream
            )

            return response

        except Exception as e:
            logger.error("AI generation failed",
                        provider=provider or self.current_provider,
                        error=str(e))
            return self._get_fallback_response()

        finally:
            processing_time = time.time() - start_time
            logger.info("AI request completed",
                       provider=provider or self.current_provider,
                       processing_time=processing_time)

    async def generate_streaming_response(
        self,
        message: str,
        context: List[Message],
        settings: Optional[ChatSettings] = None,
        provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming AI response"""

        try:
            # Get provider
            ai_provider = self.get_provider(provider)
            provider_name = provider or self.current_provider

            # Use provided settings or defaults
            chat_settings = settings or ChatSettings()

            modified_context, rag_enabled = await self._get_rag_context_and_modify_messages(message, context)

            logger.info("AI streaming request started",
                       provider=provider_name,
                       model=chat_settings.model,
                       context_length=len(modified_context),
                       rag_enabled=rag_enabled)

            # Generate streaming response using provider
            async for chunk in ai_provider.generate_streaming_response(
                message, modified_context, chat_settings
            ):
                yield chunk

        except Exception as e:
            logger.error("AI streaming generation failed",
                        provider=provider or self.current_provider,
                        error=str(e))
            yield self._get_fallback_response()

    async def _get_rag_context_and_modify_messages(self, message: str, context: List[Message]) -> tuple[List[Message], bool]:
        """Helper to retrieve RAG context and modify messages."""
        retrieved_docs = await self.vector_memory_service.query(message, top_k=self.settings.rag_top_k)
        rag_context = ""
        rag_enabled = False
        if retrieved_docs:
            rag_context = "\n\nRelevant information from memory:\n" + "\n".join([doc["document"] for doc in retrieved_docs])
            logger.info("RAG context retrieved", query=message[:50], num_docs=len(retrieved_docs))
            rag_enabled = True

        modified_context = list(context)
        if rag_context:
            if modified_context and modified_context[0].role == "system":
                modified_context[0].content += rag_context
            else:
                modified_context.insert(0, Message(content=rag_context, role="system", session_id="rag_context"))
        return modified_context, rag_enabled

    def _get_fallback_response(self) -> str:
        """Get fallback response when AI fails"""
        return self.prompt_manager.get_error_message()

    async def validate_model(self, model_name: str, provider: Optional[str] = None) -> bool:
        """Validate if model is available"""

        try:
            ai_provider = self.get_provider(provider)
            return await ai_provider.validate_model(model_name)

        except Exception as e:
            logger.warning("Model validation failed",
                          model=model_name,
                          provider=provider or self.current_provider,
                          error=str(e))
            return False

    async def get_available_models(self, provider: Optional[str] = None) -> List[str]:
        """Get list of available models for provider"""

        try:
            ai_provider = self.get_provider(provider)
            return await ai_provider.get_available_models()

        except Exception as e:
            logger.error("Failed to fetch models",
                        provider=provider or self.current_provider,
                        error=str(e))
            return []

    async def get_all_available_models(self) -> Dict[str, List[str]]:
        """Get available models for all providers"""

        all_models = {}

        for provider_name in self._providers.keys():
            try:
                provider_instance = self.get_provider(provider_name)
                models = await provider_instance.get_available_models()
                all_models[provider_name] = models
            except Exception as e:
                logger.warning("Failed to fetch models for provider",
                               provider=provider_name, error=str(e))
                all_models[provider_name] = []

        return all_models

    async def estimate_tokens(self, text: str, provider: Optional[str] = None) -> int:
        """Estimate token count for text"""

        try:
            ai_provider = self.get_provider(provider)
            return ai_provider.estimate_tokens(text)
        except Exception:
            # Fallback estimation
            return len(text) // 4

    async def health_check(self) -> Dict[str, Any]:
        """Check AI service health for all providers"""

        health_status = {
            "status": "healthy",
            "current_provider": self.current_provider,
            "providers": {}
        }

        all_healthy = True

        for provider_name in self._providers.keys():
            try:
                provider_instance = self.get_provider(provider_name)
                provider_health = await provider_instance.health_check()
                health_status["providers"][provider_name] = provider_health

                if provider_health.get("status") != "healthy":
                    all_healthy = False

            except Exception as e:
                health_status["providers"][provider_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "api_available": False
                }
                all_healthy = False

        if not all_healthy:
            health_status["status"] = "degraded"

        return health_status

    def switch_provider(self, provider_name: str) -> bool:
        """Switch to different AI provider"""

        if provider_name not in self._providers:
            logger.error("Provider not available",
                        provider=provider_name,
                        available=list(self._providers.keys()))
            return False

        # Attempt to initialize the provider to ensure it's valid
        try:
            self.get_provider(provider_name)
        except RuntimeError as e:
            logger.error("Failed to switch provider due to initialization error",
                        provider=provider_name,
                        error=str(e))
            return False

        self.current_provider = provider_name
        logger.info("Switched AI provider", provider=provider_name)
        return True

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about current provider and available providers"""

        provider_configs = {}
        for name in self._providers.keys():
            try:
                provider_instance = self.get_provider(name)
                provider_configs[name] = {
                    "name": provider_instance.get_provider_name(),
                    "model": provider_instance.config.get("model", "unknown")
                }
            except Exception as e:
                logger.warning(f"Failed to get info for provider {name}", error=str(e))
                provider_configs[name] = {"name": name, "model": "unavailable", "error": str(e)}

        return {
            "current_provider": self.current_provider,
            "available_providers": list(self._providers.keys()),
            "provider_configs": provider_configs
        }
