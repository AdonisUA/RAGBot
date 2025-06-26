"""
Google Gemini Provider implementation
"""

import time
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
import structlog
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import BaseAIProvider
from app.models.chat import Message, ChatSettings
from app.utils.prompts import PromptManager

logger = structlog.get_logger()


class GeminiProvider(BaseAIProvider):
    """Google Gemini API provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Configure Gemini
        genai.configure(api_key=config.get("api_key"))

        # Initialize model
        self.model_name = config.get("model", "gemini-pro")
        self.model = genai.GenerativeModel(self.model_name)

        self.prompt_manager = PromptManager()
        self._model_cache = {}

        # Safety settings
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

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

            # Build conversation for Gemini
            conversation_text = self._build_conversation_text(message, context, chat_settings)

            # Log request
            logger.info("Gemini request started",
                       model=self.model_name,
                       message_length=len(message),
                       context_length=len(context))

            if stream:
                # For streaming, collect all chunks
                response_text = ""
                async for chunk in self.generate_streaming_response(message, context, settings):
                    response_text += chunk
                return response_text
            else:
                return await self._generate_single_response(conversation_text, chat_settings)

        except Exception as e:
            logger.error("Gemini generation failed", error=str(e))
            return self.prompt_manager.get_error_message()

        finally:
            processing_time = time.time() - start_time
            logger.info("Gemini request completed", processing_time=processing_time)

    async def generate_streaming_response(
        self,
        message: str,
        context: List[Message],
        settings: Optional[ChatSettings] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming AI response"""

        chat_settings = settings or ChatSettings()
        conversation_text = self._build_conversation_text(message, context, chat_settings)

        # Configure generation
        generation_config = genai.types.GenerationConfig(
            temperature=chat_settings.temperature,
            top_p=chat_settings.top_p,
            max_output_tokens=chat_settings.max_tokens,
        )

        try:
            # Run in thread pool since Gemini doesn't have native async streaming
            loop = asyncio.get_event_loop()

            def _generate_stream():
                response = self.model.generate_content(
                    conversation_text,
                    generation_config=generation_config,
                    safety_settings=self.safety_settings,
                    stream=True
                )
                return response

            stream_response = await loop.run_in_executor(None, _generate_stream)

            for chunk in stream_response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error("Gemini streaming failed", error=str(e))
            yield self.prompt_manager.get_error_message()

    async def _generate_single_response(
        self,
        conversation_text: str,
        settings: ChatSettings
    ) -> str:
        """Generate single AI response"""

        # Configure generation
        generation_config = genai.types.GenerationConfig(
            temperature=settings.temperature,
            top_p=settings.top_p,
            max_output_tokens=settings.max_tokens,
        )

        # Run in thread pool since Gemini doesn't have native async
        loop = asyncio.get_event_loop()

        def _generate():
            response = self.model.generate_content(
                conversation_text,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            return response

        response = await loop.run_in_executor(None, _generate)

        if not response.text:
            raise ValueError("Empty response from Gemini")

        # Log usage (if available)
        if hasattr(response, 'usage_metadata'):
            logger.info("Gemini usage",
                       prompt_tokens=getattr(response.usage_metadata, 'prompt_token_count', 0),
                       completion_tokens=getattr(response.usage_metadata, 'candidates_token_count', 0),
                       total_tokens=getattr(response.usage_metadata, 'total_token_count', 0))

        return response.text.strip()

    def build_messages(
        self,
        user_message: str,
        context: List[Message],
        settings: ChatSettings
    ) -> List[Dict[str, Any]]:
        """Build message list for Gemini API (not used directly, but kept for interface)"""

        messages = []

        # Add system prompt as first message
        system_prompt = settings.system_prompt or self.prompt_manager.get_system_prompt()
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # Add context messages
        for msg in context[-settings.context_window:]:
            if msg.role in ["user", "assistant"]:
                # Map roles for Gemini
                role = "user" if msg.role == "user" else "model"
                messages.append({
                    "role": role,
                    "content": msg.content
                })

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    def _wrap_user_query(self, text: str) -> str:
        """Wrap user input in <user_query> and sanitize inner tags."""
        sanitized = text.replace("</user_query>", "</ user_query>")
        return f"<user_query>{sanitized}</user_query>"

    def _build_conversation_text(
        self,
        user_message: str,
        context: List[Message],
        settings: ChatSettings
    ) -> str:
        """Build conversation text for Gemini (с защитой от промпт-инъекций)"""
        conversation_parts = []
        system_prompt = settings.system_prompt or self.prompt_manager.get_system_prompt()
        if system_prompt:
            conversation_parts.append(f"System: {system_prompt}\n")
        for msg in context[-settings.context_window:]:
            if msg.role in ["user", "assistant"]:
                role_name = "Human" if msg.role == "user" else "Assistant"
                content = msg.content
                if msg.role == "user":
                    content = self._wrap_user_query(content)
                conversation_parts.append(f"{role_name}: {content}\n")
        conversation_parts.append(f"Human: {self._wrap_user_query(user_message)}\n")
        conversation_parts.append("Assistant: ")
        return "".join(conversation_parts)

    async def validate_model(self, model_name: str) -> bool:
        """Validate if model is available"""

        if model_name in self._model_cache:
            return self._model_cache[model_name]

        try:
            # Try to create model instance
            test_model = genai.GenerativeModel(model_name)

            # Try a simple generation
            loop = asyncio.get_event_loop()

            def _test_generate():
                return test_model.generate_content("Hello",
                                                 generation_config=genai.types.GenerationConfig(max_output_tokens=1))

            await loop.run_in_executor(None, _test_generate)

            self._model_cache[model_name] = True
            return True

        except Exception as e:
            logger.warning("Gemini model validation failed", model=model_name, error=str(e))
            self._model_cache[model_name] = False
            return False

    async def get_available_models(self) -> List[str]:
        """Get list of available models"""

        try:
            loop = asyncio.get_event_loop()

            def _list_models():
                models = genai.list_models()
                return [model.name.split('/')[-1] for model in models
                       if 'generateContent' in model.supported_generation_methods]

            model_names = await loop.run_in_executor(None, _list_models)
            return model_names

        except Exception as e:
            logger.error("Failed to fetch Gemini models", error=str(e))
            return ["gemini-pro", "gemini-pro-vision"]  # Fallback defaults

    async def health_check(self) -> Dict[str, Any]:
        """Check Gemini service health"""

        try:
            start_time = time.time()

            # Simple test request
            loop = asyncio.get_event_loop()

            def _test_health():
                return self.model.generate_content("Hello",
                                                 generation_config=genai.types.GenerationConfig(max_output_tokens=5))

            response = await loop.run_in_executor(None, _test_health)

            response_time = time.time() - start_time

            return {
                "status": "healthy",
                "provider": "gemini",
                "model": self.model_name,
                "response_time": response_time,
                "api_available": True
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "gemini",
                "error": str(e),
                "api_available": False
            }
