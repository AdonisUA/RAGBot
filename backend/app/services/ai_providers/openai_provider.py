"""
OpenAI Provider implementation
"""

import time
from typing import List, Dict, Any, Optional, AsyncGenerator
import structlog
from openai import AsyncOpenAI

from .base import BaseAIProvider
from app.models.chat import Message, ChatSettings
from app.utils.prompts import PromptManager

logger = structlog.get_logger()


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url", "https://api.openai.com/v1")
        )
        self.prompt_manager = PromptManager()
        self._model_cache = {}

    async def generate_response(
        self,
        message: str,
        context: List[Message],
        settings: Optional[ChatSettings] = None,
        stream: bool = False
    ) -> str:
        """Generate AI response for user message"""

        start_time = time.time()

        try:
            # Use provided settings or defaults
            chat_settings = settings or ChatSettings()

            # Build messages for OpenAI
            messages = self.build_messages(message, context, chat_settings)

            # Log request
            logger.info("OpenAI request started",
                       model=chat_settings.model,
                       message_length=len(message),
                       context_length=len(context))

            if stream:
                # For streaming, collect all chunks
                response_text = ""
                async for chunk in self.generate_streaming_response(message, context, settings):
                    response_text += chunk
                return response_text
            else:
                return await self._generate_single_response(messages, chat_settings)

        except Exception as e:
            logger.error("OpenAI generation failed", error=str(e))
            return self.prompt_manager.get_error_message()

        finally:
            processing_time = time.time() - start_time
            logger.info("OpenAI request completed", processing_time=processing_time)

    async def generate_streaming_response(
        self,
        message: str,
        context: List[Message],
        settings: Optional[ChatSettings] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming AI response"""

        chat_settings = settings or ChatSettings()
        messages = self.build_messages(message, context, chat_settings)

        stream = await self.client.chat.completions.create(
            model=chat_settings.model,
            messages=messages,
            temperature=chat_settings.temperature,
            max_tokens=chat_settings.max_tokens,
            top_p=chat_settings.top_p,
            frequency_penalty=chat_settings.frequency_penalty,
            presence_penalty=chat_settings.presence_penalty,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _generate_single_response(
        self,
        messages: List[Dict[str, str]],
        settings: ChatSettings
    ) -> str:
        """Generate single AI response"""

        response = await self.client.chat.completions.create(
            model=settings.model,
            messages=messages,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            top_p=settings.top_p,
            frequency_penalty=settings.frequency_penalty,
            presence_penalty=settings.presence_penalty
        )

        # Extract response text
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        # Log usage
        if response.usage:
            logger.info("OpenAI usage",
                       prompt_tokens=response.usage.prompt_tokens,
                       completion_tokens=response.usage.completion_tokens,
                       total_tokens=response.usage.total_tokens)

        return content.strip()

    def _wrap_user_query(self, text: str) -> str:
        """Wrap user input in <user_query> and sanitize inner tags."""
        sanitized = text.replace("</user_query>", "</ user_query>")
        return f"<user_query>{sanitized}</user_query>"

    def build_messages(
        self,
        user_message: str,
        context: List[Message],
        settings: ChatSettings
    ) -> List[Dict[str, str]]:
        """Build message list for OpenAI API (с защитой от промпт-инъекций)"""
        messages = []
        system_prompt = settings.system_prompt or self.prompt_manager.get_system_prompt()
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        for msg in context[-settings.context_window:]:
            if msg.role in ["user", "assistant"]:
                content = msg.content
                if msg.role == "user":
                    content = self._wrap_user_query(content)
                messages.append({
                    "role": msg.role,
                    "content": content
                })
        messages.append({
            "role": "user",
            "content": self._wrap_user_query(user_message)
        })
        return messages

    async def validate_model(self, model_name: str) -> bool:
        """Validate if model is available"""

        if model_name in self._model_cache:
            return self._model_cache[model_name]

        try:
            # Try to make a simple request to validate model
            await self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            self._model_cache[model_name] = True
            return True

        except Exception as e:
            logger.warning("OpenAI model validation failed", model=model_name, error=str(e))
            self._model_cache[model_name] = False
            return False

    async def get_available_models(self) -> List[str]:
        """Get list of available models"""

        try:
            models = await self.client.models.list()
            return [model.id for model in models.data if "gpt" in model.id]
        except Exception as e:
            logger.error("Failed to fetch OpenAI models", error=str(e))
            return ["gpt-3.5-turbo", "gpt-4"]  # Fallback defaults

    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI service health"""

        try:
            start_time = time.time()

            # Simple test request
            response = await self.client.chat.completions.create(
                model=self.config.get("model", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )

            response_time = time.time() - start_time

            return {
                "status": "healthy",
                "provider": "openai",
                "model": self.config.get("model", "gpt-3.5-turbo"),
                "response_time": response_time,
                "api_available": True
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "openai",
                "error": str(e),
                "api_available": False
            }
