

"""
Voice API endpoints for AI ChatBot
Handles audio upload and speech-to-text processing
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional
import structlog
from uuid import uuid4

from app.models.voice import (
    VoiceRequest,
    VoiceResponse,
    TranscriptionResult,
    AudioFile,
    VoiceSettings,
    AudioProcessingStatus
)
from app.services.voice_service import VoiceService
from app.services.memory_service import MemoryService
from app.models.chat import Message
from app.core.exceptions import VoiceServiceException, MemoryServiceException

logger = structlog.get_logger()
router = APIRouter()


def get_voice_service() -> VoiceService:
    """Dependency to get voice service instance"""
    return VoiceService()


def get_memory_service() -> MemoryService:
    """Dependency to get memory service instance"""
    return MemoryService()


@router.post("/transcribe", response_model=VoiceResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    language: Optional[str] = Form("auto"),
    task: str = Form("transcribe"),
    auto_send: bool = Form(True),
    voice_service: VoiceService = Depends(get_voice_service),
    memory_service: MemoryService = Depends(get_memory_service)
) -> VoiceResponse:
    """Transcribe uploaded audio file"""

    try:
        # Validate file
        if not audio.content_type or not audio.content_type.startswith('audio/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an audio file"
            )

        # Read audio data
        audio_data = await audio.read()

        # Create audio file metadata
        audio_file = AudioFile(
            filename=audio.filename or "uploaded_audio",
            content_type=audio.content_type,
            size_bytes=len(audio_data)
        )

        logger.info("Audio upload received",
                   filename=audio_file.filename,
                   size_bytes=audio_file.size_bytes,
                   content_type=audio_file.content_type,
                   session_id=session_id)

        # Validate audio
        if not await voice_service.validate_audio(audio_data, audio_file.content_type):
            raise HTTPException(
                status_code=400,
                detail="Invalid audio file or format not supported"
            )

        # Create voice settings
        voice_settings = VoiceSettings(
            language=language,
            task=task
        )

        # Transcribe audio
        transcription = await voice_service.transcribe_audio(
            audio_data,
            audio_file,
            voice_settings
        )

        # Handle auto-send to chat
        chat_message_id = None
        if auto_send and session_id and transcription.text:
            try:
                # Create chat message from transcription
                message = Message(
                    content=transcription.text,
                    role="user",
                    session_id=session_id,
                    metadata={
                        "source": "voice",
                        "audio_id": audio_file.id,
                        "confidence": transcription.confidence
                    }
                )

                # Save to memory
                await memory_service.add_message(session_id, message)
                chat_message_id = message.id

                logger.info("Voice transcription auto-sent to chat",
                           session_id=session_id,
                           message_id=chat_message_id)

            except Exception as e:
                logger.warning("Failed to auto-send transcription to chat",
                              error=str(e))

        # Create response
        response = VoiceResponse(
            transcription=transcription,
            audio_id=audio_file.id,
            session_id=session_id,
            auto_sent_to_chat=bool(chat_message_id),
            chat_message_id=chat_message_id,
            metadata={
                "original_filename": audio_file.filename,
                "processing_time": transcription.processing_time
            }
        )

        logger.info("Voice transcription completed",
                   audio_id=audio_file.id,
                   text_length=len(transcription.text),
                   confidence=transcription.confidence,
                   auto_sent=bool(chat_message_id))

        return response

    except VoiceServiceException as e:
        logger.error("Voice service error", error=str(e))
        raise HTTPException(status_code=503, detail=str(e))

    except MemoryServiceException as e:
        logger.error("Memory service error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error in voice transcription", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status/{audio_id}", response_model=AudioProcessingStatus)
async def get_processing_status(
    audio_id: str,
    voice_service: VoiceService = Depends(get_voice_service)
) -> AudioProcessingStatus:
    """Get audio processing status"""

    try:
        status = voice_service.get_processing_status(audio_id)

        if not status:
            raise HTTPException(status_code=404, detail="Audio processing not found")

        return status

    except Exception as e:
        logger.error("Error getting processing status", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/validate")
async def validate_audio_file(
    audio: UploadFile = File(...),
    voice_service: VoiceService = Depends(get_voice_service)
) -> dict:
    """Validate audio file without processing"""

    try:
        # Read audio data
        audio_data = await audio.read()

        # Validate
        is_valid = await voice_service.validate_audio(
            audio_data,
            audio.content_type or "audio/wav"
        )

        return {
            "valid": is_valid,
            "filename": audio.filename,
            "content_type": audio.content_type,
            "size_bytes": len(audio_data)
        }

    except Exception as e:
        logger.error("Error validating audio", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/settings", response_model=VoiceSettings)
async def get_voice_settings() -> VoiceSettings:
    """Get current voice processing settings"""

    return VoiceSettings()


@router.post("/settings", response_model=VoiceSettings)
async def update_voice_settings(
    settings: VoiceSettings
) -> VoiceSettings:
    """Update voice processing settings"""

    # In a real implementation, you would save these settings
    # For now, just return the provided settings
    logger.info("Voice settings updated", settings=settings.dict())

    return settings


@router.get("/models")
async def list_available_models() -> dict:
    """List available Whisper models"""

    models = [
        {
            "name": "tiny",
            "size": "39 MB",
            "speed": "Very Fast",
            "accuracy": "Low"
        },
        {
            "name": "base",
            "size": "74 MB",
            "speed": "Fast",
            "accuracy": "Medium"
        },
        {
            "name": "small",
            "size": "244 MB",
            "speed": "Medium",
            "accuracy": "Good"
        },
        {
            "name": "medium",
            "size": "769 MB",
            "speed": "Slow",
            "accuracy": "Very Good"
        },
        {
            "name": "large",
            "size": "1550 MB",
            "speed": "Very Slow",
            "accuracy": "Excellent"
        }
    ]

    return {
        "models": models,
        "current_model": "base",  # From settings
        "supported_languages": [
            "auto", "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"
        ]
    }


@router.get("/health")
async def voice_health_check(
    voice_service: VoiceService = Depends(get_voice_service)
) -> dict:
    """Voice service health check"""

    try:
        health_status = await voice_service.health_check()
        return health_status

    except Exception as e:
        logger.error("Voice health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }
