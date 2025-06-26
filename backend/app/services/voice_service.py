"""
Voice Service for Whisper integration
Handles speech-to-text transcription
"""

import asyncio
import tempfile
import time
import os
import json
from typing import Optional, Dict, Any
import structlog
import whisper
import torch
from pydub import AudioSegment
import io
import aioredis

from app.core.config import get_settings
from app.models.voice import (
    AudioFile,
    TranscriptionResult,
    VoiceSettings,
    AudioProcessingStatus
)

logger = structlog.get_logger()


class VoiceService:
    """Whisper speech-to-text service"""

    def __init__(self):
        self.settings = get_settings()
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.redis = aioredis.from_url(self.settings.redis_url, decode_responses=True)
        self.status_ttl = 3600 # 1 hour TTL for processing status keys

    async def initialize(self):
        """Initialize Whisper model"""

        try:
            logger.info("Loading Whisper model",
                       model=self.settings.whisper_model,
                       device=self.device)

            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                whisper.load_model,
                self.settings.whisper_model,
                self.device
            )

            logger.info("Whisper model loaded successfully")

        except Exception as e:
            logger.error("Failed to load Whisper model", error=str(e))
            raise

    async def transcribe_audio(
        self,
        audio_data: bytes,
        audio_file: AudioFile,
        settings: Optional[VoiceSettings] = None
    ) -> TranscriptionResult:
        """Transcribe audio to text"""

        if not self.model:
            await self.initialize()

        start_time = time.time()
        audio_id = audio_file.id

        try:
            # Update processing status
            self._update_status(audio_id, "processing", 0)

            # Use provided settings or defaults
            voice_settings = settings or VoiceSettings()

            # Process audio file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                # Convert audio to WAV format
                audio_segment = await self._convert_audio(audio_data, audio_file)
                audio_segment.export(temp_file.name, format="wav")

                self._update_status(audio_id, "processing", 25)

                # Transcribe with Whisper
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._transcribe_with_whisper,
                    temp_file.name,
                    voice_settings
                )

                self._update_status(audio_id, "processing", 75)

                # Clean up temp file
                os.unlink(temp_file.name)

            processing_time = time.time() - start_time

            # Create transcription result
            transcription = TranscriptionResult(
                text=result["text"].strip(),
                confidence=self._calculate_confidence(result),
                language=result.get("language"),
                duration=audio_file.duration_seconds,
                segments=result.get("segments"),
                processing_time=processing_time
            )

            self._update_status(audio_id, "completed", 100)

            logger.info("Transcription completed",
                       audio_id=audio_id,
                       text_length=len(transcription.text),
                       processing_time=processing_time,
                       confidence=transcription.confidence)

            return transcription

        except Exception as e:
            self._update_status(audio_id, "failed", 0, error=str(e))
            logger.error("Transcription failed",
                        audio_id=audio_id,
                        error=str(e))
            raise

    def _transcribe_with_whisper(
        self,
        audio_path: str,
        settings: VoiceSettings
    ) -> Dict[str, Any]:
        """Perform Whisper transcription (blocking)"""

        options = {
            "language": settings.language if settings.language != "auto" else None,
            "task": settings.task,
            "temperature": settings.temperature,
            "best_of": settings.best_of,
            "beam_size": settings.beam_size,
            "patience": settings.patience,
            "length_penalty": settings.length_penalty,
            "suppress_tokens": settings.suppress_tokens,
            "initial_prompt": settings.initial_prompt,
            "condition_on_previous_text": settings.condition_on_previous_text,
            "fp16": settings.fp16,
            "compression_ratio_threshold": settings.compression_ratio_threshold,
            "logprob_threshold": settings.logprob_threshold,
            "no_speech_threshold": settings.no_speech_threshold
        }

        # Remove None values
        options = {k: v for k, v in options.items() if v is not None}

        return self.model.transcribe(audio_path, **options)

    async def _convert_audio(
        self,
        audio_data: bytes,
        audio_file: AudioFile
    ) -> AudioSegment:
        """Convert audio to standard format"""

        try:
            # Detect format from content type
            format_map = {
                "audio/wav": "wav",
                "audio/wave": "wav",
                "audio/x-wav": "wav",
                "audio/mp3": "mp3",
                "audio/mpeg": "mp3",
                "audio/mp4": "mp4",
                "audio/m4a": "m4a",
                "audio/ogg": "ogg",
                "audio/webm": "webm"
            }

            audio_format = format_map.get(audio_file.content_type, "wav")

            # Load audio with pydub
            audio_segment = AudioSegment.from_file(
                io.BytesIO(audio_data),
                format=audio_format
            )

            # Convert to standard format for Whisper
            audio_segment = audio_segment.set_frame_rate(self.settings.audio_sample_rate)
            audio_segment = audio_segment.set_channels(self.settings.audio_channels)

            return audio_segment

        except Exception as e:
            logger.error("Audio conversion failed", error=str(e))
            raise ValueError(f"Failed to process audio: {str(e)}")

    def _calculate_confidence(self, whisper_result: Dict[str, Any]) -> Optional[float]:
        """Calculate confidence score from Whisper result"""

        if "segments" not in whisper_result:
            return None

        segments = whisper_result["segments"]
        if not segments:
            return None

        # Average confidence from segments
        total_confidence = 0
        total_duration = 0

        for segment in segments:
            if "avg_logprob" in segment and "end" in segment and "start" in segment:
                duration = segment["end"] - segment["start"]
                confidence = min(1.0, max(0.0, (segment["avg_logprob"] + 1.0)))
                total_confidence += confidence * duration
                total_duration += duration

        if total_duration > 0:
            return total_confidence / total_duration

        return None

    async def _update_status(
        self,
        audio_id: str,
        status: str,
        progress: float,
        error: Optional[str] = None
    ):
        """Update processing status in Redis"""
        key = f"voice_status:{audio_id}"
        current_status_data = await self.redis.get(key)
        if current_status_data:
            current_status = AudioProcessingStatus.parse_raw(current_status_data)
        else:
            current_status = AudioProcessingStatus(
                audio_id=audio_id,
                status="uploaded", # Initial status if not found
                progress=0.0,
                started_at=time.time()
            )

        # Update fields
        current_status.status = status
        current_status.progress = progress
        current_status.error = error
        if status in ["completed", "failed"]:
            current_status.completed_at = time.time()
            current_status.processing_time = current_status.completed_at - current_status.started_at

        await self.redis.setex(key, self.status_ttl, current_status.json())

    async def get_processing_status(self, audio_id: str) -> Optional[AudioProcessingStatus]:
        """Get processing status for audio from Redis"""
        key = f"voice_status:{audio_id}"
        status_data = await self.redis.get(key)
        if status_data:
            return AudioProcessingStatus.parse_raw(status_data)
        return None

    async def validate_audio(self, audio_data: bytes, content_type: str) -> bool:
        """Validate audio file"""

        try:
            # Check file size
            if len(audio_data) > 25 * 1024 * 1024:  # 25MB
                return False

            # Try to load with pydub
            format_map = {
                "audio/wav": "wav",
                "audio/mp3": "mp3",
                "audio/mp4": "mp4",
                "audio/m4a": "m4a",
                "audio/ogg": "ogg"
            }

            audio_format = format_map.get(content_type)
            if not audio_format:
                return False

            audio_segment = AudioSegment.from_file(
                io.BytesIO(audio_data),
                format=audio_format
            )

            # Check duration
            duration = len(audio_segment) / 1000.0  # Convert to seconds
            if duration > self.settings.max_audio_duration:
                return False

            return True

        except Exception:
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check voice service health"""

        try:
            if not self.model:
                return {
                    "status": "unhealthy",
                    "error": "Model not loaded",
                    "model_loaded": False
                }

            return {
                "status": "healthy",
                "model": self.settings.whisper_model,
                "device": self.device,
                "model_loaded": True
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model_loaded": False
            }

    async def cleanup(self):
        """Cleanup resources"""

        if self.model:
            del self.model
            self.model = None

        # Clear CUDA cache if using GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Voice service cleaned up")
