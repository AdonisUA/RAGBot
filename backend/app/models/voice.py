"""
Voice processing data models for AI ChatBot
Models for audio handling and speech recognition
"""

from pydantic import Field, field_validator
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4
from app.models import BaseAppModel


class AudioFile(BaseAppModel):
    """Audio file metadata"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str = Field(...)
    content_type: str = Field(...)
    size_bytes: int = Field(..., gt=0)
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    format: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        """Validate audio content type"""
        allowed_types = [
            "audio/wav", "audio/wave", "audio/x-wav",
            "audio/mp3", "audio/mpeg",
            "audio/mp4", "audio/m4a",
            "audio/ogg", "audio/webm"
        ]
        if v not in allowed_types:
            raise ValueError(f"Unsupported audio format: {v}")
        return v.strip()

    @field_validator("size_bytes")
    @classmethod
    def validate_size_bytes(cls, v):
        """Validate file size (max 25MB)"""
        max_size = 25 * 1024 * 1024  # 25MB
        if v > max_size:
            raise ValueError(f"File too large: {v} bytes (max: {max_size})")
        return v


class VoiceRequest(BaseAppModel):
    """Voice transcription request"""
    audio_id: Optional[str] = None
    session_id: Optional[str] = None
    language: Optional[str] = Field("auto", description="Language code or 'auto'")
    task: Literal["transcribe", "translate"] = Field("transcribe")
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    auto_send: bool = Field(True, description="Auto-send transcribed text to chat")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TranscriptionResult(BaseAppModel):
    """Speech-to-text transcription result"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str = Field(...)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    language: Optional[str] = None
    duration: Optional[float] = None
    segments: Optional[list] = None
    processing_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        """Validate transcribed text"""
        if not v or not v.strip():
            raise ValueError("Transcription cannot be empty")
        return v.strip()


class VoiceResponse(BaseAppModel):
    """Voice processing response"""
    transcription: TranscriptionResult = Field(...)
    audio_id: str = Field(...)
    session_id: Optional[str] = None
    auto_sent_to_chat: bool = Field(False)
    chat_message_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceSettings(BaseAppModel):
    """Voice processing settings"""
    model: Literal["tiny", "base", "small", "medium", "large"] = Field("base")
    language: Optional[str] = Field("auto")
    task: Literal["transcribe", "translate"] = Field("transcribe")
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    best_of: int = Field(1, ge=1, le=5)
    beam_size: int = Field(5, ge=1, le=10)
    patience: Optional[float] = Field(None, ge=0.0, le=2.0)
    length_penalty: Optional[float] = Field(None, ge=-1.0, le=1.0)
    suppress_tokens: Optional[str] = Field("-1")
    initial_prompt: Optional[str] = None
    condition_on_previous_text: bool = Field(True)
    fp16: bool = Field(True)
    compression_ratio_threshold: float = Field(2.4, ge=0.0, le=10.0)
    logprob_threshold: float = Field(-1.0, ge=-10.0, le=0.0)
    no_speech_threshold: float = Field(0.6, ge=0.0, le=1.0)


class AudioProcessingStatus(BaseAppModel):
    """Audio processing status"""
    audio_id: str = Field(...)
    status: Literal["uploaded", "processing", "completed", "failed"] = Field(...)
    progress: float = Field(0.0, ge=0.0, le=100.0)
    message: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None


from pydantic import Field, field_validator
from typing import Optional, Dict, Any, Literal, Union
from datetime import datetime
from uuid import uuid4
from app.models import BaseAppModel


class AudioFile(BaseAppModel):
    """Audio file metadata"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str = Field(...)
    content_type: str = Field(...)
    size_bytes: int = Field(..., gt=0)
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    format: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        """Validate audio content type"""
        allowed_types = [
            "audio/wav", "audio/wave", "audio/x-wav",
            "audio/mp3", "audio/mpeg",
            "audio/mp4", "audio/m4a",
            "audio/ogg", "audio/webm"
        ]
        if v not in allowed_types:
            raise ValueError(f"Unsupported audio format: {v}")
        return v.strip()

    @field_validator("size_bytes")
    @classmethod
    def validate_size_bytes(cls, v):
        """Validate file size (max 25MB)"""
        max_size = 25 * 1024 * 1024  # 25MB
        if v > max_size:
            raise ValueError(f"File too large: {v} bytes (max: {max_size})")
        return v


class VoiceRequest(BaseAppModel):
    """Voice transcription request"""
    audio_id: Optional[str] = None
    session_id: Optional[str] = None
    language: Optional[str] = Field("auto", description="Language code or 'auto'")
    task: Literal["transcribe", "translate"] = Field("transcribe")
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    auto_send: bool = Field(True, description="Auto-send transcribed text to chat")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TranscriptionResult(BaseAppModel):
    """Speech-to-text transcription result"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str = Field(...)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    language: Optional[str] = None
    duration: Optional[float] = None
    segments: Optional[list] = None
    processing_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        """Validate transcribed text"""
        if not v or not v.strip():
            raise ValueError("Transcription cannot be empty")
        return v.strip()


class VoiceResponse(BaseAppModel):
    """Voice processing response"""
    transcription: TranscriptionResult = Field(...)
    audio_id: str = Field(...)
    session_id: Optional[str] = None
    auto_sent_to_chat: bool = Field(False)
    chat_message_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceSettings(BaseAppModel):
    """Voice processing settings"""
    model: Literal["tiny", "base", "small", "medium", "large"] = Field("base")
    language: Optional[str] = Field("auto")
    task: Literal["transcribe", "translate"] = Field("transcribe")
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    best_of: int = Field(1, ge=1, le=5)
    beam_size: int = Field(5, ge=1, le=10)
    patience: Optional[float] = Field(None, ge=0.0, le=2.0)
    length_penalty: Optional[float] = Field(None, ge=-1.0, le=1.0)
    suppress_tokens: Optional[str] = Field("-1")
    initial_prompt: Optional[str] = None
    condition_on_previous_text: bool = Field(True)
    fp16: bool = Field(True)
    compression_ratio_threshold: float = Field(2.4, ge=0.0, le=10.0)
    logprob_threshold: float = Field(-1.0, ge=-10.0, le=0.0)
    no_speech_threshold: float = Field(0.6, ge=0.0, le=1.0)


class AudioProcessingStatus(BaseAppModel):
    """Audio processing status"""
    audio_id: str = Field(...)
    status: Literal["uploaded", "processing", "completed", "failed"] = Field(...)
    progress: float = Field(0.0, ge=0.0, le=100.0)
    message: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None


class AudioChunk(BaseAppModel):
    """Real-time audio chunk for streaming"""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    audio_id: str = Field(...)
    sequence: int = Field(..., ge=0)
    data: bytes = Field(...)
    is_final: bool = Field(False)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class VoiceMetrics(BaseAppModel):
    """Voice processing metrics"""
    total_requests: int = Field(0)
    successful_transcriptions: int = Field(0)
    failed_transcriptions: int = Field(0)
    average_processing_time: float = Field(0.0)
    average_confidence: float = Field(0.0)
    total_audio_duration: float = Field(0.0)
    supported_languages: list = Field(default_factory=list)
    model_performance: Dict[str, Any] = Field(default_factory=dict)


# Specific WebSocket data models for voice
class AudioChunkWebSocketData(BaseAppModel):
    chunk_id: str = Field(...)
    audio_id: str = Field(...)
    sequence: int = Field(...)
    data: str = Field(...) # Base64 encoded audio data
    is_final: bool = Field(...)

class TranscriptionWebSocketData(BaseAppModel):
    audio_id: str = Field(...)
    text: str = Field(...)
    confidence: Optional[float] = None

class VoiceStatusWebSocketData(BaseAppModel):
    audio_id: str = Field(...)
    status: Literal["uploaded", "processing", "completed", "failed"] = Field(...)
    progress: float = Field(...)
    message: Optional[str] = None

class VoiceErrorWebSocketData(BaseAppModel):
    audio_id: str = Field(...)
    message: str = Field(...)
    code: Optional[str] = None

class VoiceWebSocketMessage(BaseAppModel):
    """WebSocket message for voice processing"""
    type: Literal["audio_chunk", "transcription", "status", "error", "voice_status", "voice_transcription"] = Field(...)
    data: Union[AudioChunkWebSocketData, TranscriptionWebSocketData, VoiceStatusWebSocketData, VoiceErrorWebSocketData, Dict[str, Any]] = Field(...)
    audio_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AudioChunk(BaseAppModel):
    """Real-time audio chunk for streaming"""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    audio_id: str = Field(...)
    sequence: int = Field(..., ge=0)
    data: bytes = Field(...)
    is_final: bool = Field(False)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class VoiceMetrics(BaseAppModel):
    """Voice processing metrics"""
    total_requests: int = Field(0)
    successful_transcriptions: int = Field(0)
    failed_transcriptions: int = Field(0)
    average_processing_time: float = Field(0.0)
    average_confidence: float = Field(0.0)
    total_audio_duration: float = Field(0.0)
    supported_languages: list = Field(default_factory=list)
    model_performance: Dict[str, Any] = Field(default_factory=dict)
