

"""
Chat API endpoints for AI ChatBot
Handles text-based chat interactions
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
import structlog
from uuid import uuid4

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistory,
    ConversationSummary,
    Message,
    ChatSettings
)
from app.services.ai_service import AIService
from app.services.memory_service import MemoryService
from app.core.exceptions import AIServiceException, MemoryServiceException
from app.services.message_handler_service import MessageHandlerService
from app.services.research_service import ResearchService
logger = structlog.get_logger()
router = APIRouter()


def get_ai_service() -> AIService:
    """Dependency to get AI service instance"""
    return AIService()


def get_memory_service() -> MemoryService:
    """Dependency to get memory service instance"""
    return MemoryService()


def get_message_handler_service() -> MessageHandlerService:
    return MessageHandlerService()

def get_research_service() -> ResearchService:
    return ResearchService()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    provider: Optional[str] = None,
    handler_service: MessageHandlerService = Depends(get_message_handler_service)
) -> ChatResponse:
    """Send a chat message and get AI response"""

    try:
        user_msg = Message(content=request.message, role="user", session_id=request.session_id)
        result = await handler_service.process_message(request.session_id, user_msg)
        return ChatResponse(
            response=result["message"],
            session_id=result["session_id"],
            message_id=result["message_id"],
            metadata={
                "context_length": 10,
                "user_message_id": user_msg.id
            }
        )

    except ChatBotException as e:
        logger.error("ChatBot exception in chat endpoint",
                    exception_type=type(e).__name__,
                    message=e.message,
                    code=e.code,
                    details=e.details)
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error in chat endpoint", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history/{session_id}", response_model=ChatHistory)
async def get_chat_history(
    session_id: str,
    page: int = 1,
    page_size: int = 50,
    memory_service: MemoryService = Depends(get_memory_service)
) -> ChatHistory:
    """Get chat history for a session"""

    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="Page size must be between 1 and 100")

        # Calculate offset
        offset = (page - 1) * page_size

        # Get messages
        messages = await memory_service.get_conversation_history(
            session_id,
            limit=page_size + 1,  # Get one extra to check if there are more
            offset=offset
        )

        # Check if there are more messages
        has_more = len(messages) > page_size
        if has_more:
            messages = messages[:page_size]

        # Get total message count
        conversation = await memory_service.load_conversation(session_id)
        total_messages = conversation.message_count if conversation else 0

        logger.info("Chat history retrieved",
                   session_id=session_id,
                   page=page,
                   page_size=page_size,
                   returned_messages=len(messages))

        return ChatHistory(
            session_id=session_id,
            messages=messages,
            total_messages=total_messages,
            page=page,
            page_size=page_size,
            has_more=has_more
        )

    except MemoryServiceException as e:
        logger.error("Memory service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error getting history", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    memory_service: MemoryService = Depends(get_memory_service)
) -> List[ConversationSummary]:
    """List all conversations"""

    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > 50:
            raise HTTPException(status_code=400, detail="Page size must be between 1 and 50")

        # Calculate offset
        offset = (page - 1) * page_size

        # Get conversations
        conversations = await memory_service.list_conversations(
            limit=page_size,
            offset=offset
        )

        logger.info("Conversations listed",
                   page=page,
                   page_size=page_size,
                   returned_count=len(conversations))

        return conversations

    except MemoryServiceException as e:
        logger.error("Memory service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error listing conversations", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/conversation/{session_id}")
async def delete_conversation(
    session_id: str,
    memory_service: MemoryService = Depends(get_memory_service)
) -> dict:
    """Delete a conversation"""

    try:
        success = await memory_service.delete_conversation(session_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        logger.info("Conversation deleted", session_id=session_id)

        return {"message": "Conversation deleted successfully"}

    except MemoryServiceException as e:
        logger.error("Memory service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error deleting conversation", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversation/{session_id}/export")
async def export_conversation(
    session_id: str,
    format: str = "json",
    memory_service: MemoryService = Depends(get_memory_service)
):
    """Export conversation in specified format"""

    try:
        # Validate format
        if format not in ["json", "txt", "markdown"]:
            raise HTTPException(
                status_code=400,
                detail="Format must be one of: json, txt, markdown"
            )

        # Export conversation
        exported_data = await memory_service.export_conversation(session_id, format)

        if not exported_data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Set content type and filename
        content_types = {
            "json": "application/json",
            "txt": "text/plain",
            "markdown": "text/markdown"
        }

        filename = f"conversation_{session_id}.{format}"

        logger.info("Conversation exported",
                   session_id=session_id,
                   format=format)

        return StreamingResponse(
            iter([exported_data]),
            media_type=content_types[format],
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except MemoryServiceException as e:
        logger.error("Memory service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error exporting conversation", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/cleanup")
async def cleanup_old_conversations(
    max_age_days: int = 30,
    memory_service: MemoryService = Depends(get_memory_service)
) -> dict:
    """Cleanup old conversations"""

    try:
        if max_age_days < 1:
            raise HTTPException(status_code=400, detail="Max age must be >= 1 day")

        deleted_count = await memory_service.cleanup_old_conversations(max_age_days)

        logger.info("Conversations cleaned up",
                   max_age_days=max_age_days,
                   deleted_count=deleted_count)

        return {
            "message": f"Cleaned up {deleted_count} old conversations",
            "deleted_count": deleted_count,
            "max_age_days": max_age_days
        }

    except MemoryServiceException as e:
        logger.error("Memory service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error during cleanup", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/clear_all_conversations")
async def clear_all_conversations(
    memory_service: MemoryService = Depends(get_memory_service)
) -> dict:
    """Clear all conversations"""

    try:
        deleted_count = await memory_service.clear_all_conversations()

        logger.info("All conversations cleared", deleted_count=deleted_count)

        return {
            "message": f"Cleared {deleted_count} conversations",
            "deleted_count": deleted_count
        }

    except MemoryServiceException as e:
        logger.error("Memory service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error during clearing all conversations", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/providers")
async def get_ai_providers(
    ai_service: AIService = Depends(get_ai_service)
) -> dict:
    """Get information about available AI providers"""

    try:
        provider_info = ai_service.get_provider_info()
        return provider_info

    except Exception as e:
        logger.error("Error getting provider info", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/providers/switch")
async def switch_ai_provider(
    provider: str,
    ai_service: AIService = Depends(get_ai_service)
) -> dict:
    """Switch to different AI provider"""

    try:
        success = ai_service.switch_provider(provider)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider}' not available"
            )

        return {
            "message": f"Switched to provider: {provider}",
            "current_provider": provider
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error switching provider", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/models")
async def get_available_models(
    provider: Optional[str] = None,
    ai_service: AIService = Depends(get_ai_service)
) -> dict:
    """Get available models for provider(s)"""

    try:
        if provider:
            # Get models for specific provider
            models = await ai_service.get_available_models(provider)
            return {
                "provider": provider,
                "models": models
            }
        else:
            # Get models for all providers
            all_models = await ai_service.get_all_available_models()
            return {
                "providers": all_models
            }

    except Exception as e:
        logger.error("Error getting available models", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
