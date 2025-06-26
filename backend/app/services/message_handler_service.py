import structlog
import uuid
import asyncio
from datetime import datetime
from typing import Optional
from app.services.ai_service import AIService
from app.services.memory_service import MemoryService
from app.services.vector_memory_service import VectorMemoryService
from app.models.chat import Message
from app.core.exceptions import AIServiceException, MemoryServiceException, ChatBotException
from app.services.research_service import ResearchService

logger = structlog.get_logger()

class MessageHandlerService:
    def __init__(
        self,
        ai_service: AIService = AIService(),
        memory_service: MemoryService = MemoryService(),
        vector_memory_service: VectorMemoryService = VectorMemoryService(),
        research_service: ResearchService = ResearchService()
    ): # Default to creating new instances for backward compatibility/simplicity if not injected
        self.ai_service = ai_service
        self.memory_service = memory_service
        self.vector_memory_service = vector_memory_service
        self.research_service = research_service

    async def process_message(self, session_id: Optional[str], message: Message) -> dict:
        if not message.content.strip():
            raise ChatBotException(message="Empty message", code="EMPTY_MESSAGE")

        if not session_id:
            session_id = str(uuid.uuid4())
        message.session_id = session_id

        try:
            await self.memory_service.add_message(session_id, message)
        except Exception as e:
            logger.error("Error adding user message to memory", error=str(e), session_id=session_id, message_id=message.id)
            raise MemoryServiceException(message="Failed to save user message", details={"original_error": str(e)})

        context = await self.memory_service.get_conversation_history(session_id, limit=10)

        try:
            ai_response = await self.ai_service.generate_response(
                message.content,
                context[:-1]  # Exclude current message from context
            )
        except Exception as e:
            logger.error("Error generating AI response", error=str(e), session_id=session_id, user_message_id=message.id)
            raise AIServiceException(message="Failed to generate AI response", details={"original_error": str(e)})

        ai_msg = Message(
            content=ai_response,
            role="assistant",
            session_id=session_id
        )

        try:
            await self.memory_service.add_message(session_id, ai_msg)
        except Exception as e:
            logger.error("Error adding AI message to memory", error=str(e), session_id=session_id, message_id=ai_msg.id)
            raise MemoryServiceException(message="Failed to save AI message", details={"original_error": str(e)})

        # Background task for populating vector memory (RAG pipeline)
        asyncio.create_task(
            self._populate_vector_memory(message.content, ai_response, session_id)
        )

        # Trigger research agent if needed
        try:
            await self.research_service.trigger_research_if_needed(message.content, ai_response, session_id)
        except Exception as e:
            logger.error("Failed to trigger research agent", error=str(e), session_id=session_id)

        return {
            "message": ai_response,
            "message_id": ai_msg.id,
            "session_id": session_id,
            "role": "assistant"
        }

    async def _populate_vector_memory(self, user_query: str, ai_response: str, session_id: str):
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.memory_service.settings.rag_chunk_size,
                chunk_overlap=self.memory_service.settings.rag_chunk_overlap
            )
            combined_text = f"User: {user_query}\nAI: {ai_response}"
            chunks = text_splitter.split_text(combined_text)

            for i, chunk in enumerate(chunks):
                metadata = {
                    "session_id": session_id,
                    "type": "conversation_chunk",
                    "timestamp": datetime.now().isoformat(),
                    "chunk_index": i
                }
                await self.vector_memory_service.add_document(chunk, metadata)
            logger.info("Vector memory populated with conversation chunks", session_id=session_id, num_chunks=len(chunks))
        except Exception as e:
            logger.error("Failed to populate vector memory", error=str(e), session_id=session_id)
