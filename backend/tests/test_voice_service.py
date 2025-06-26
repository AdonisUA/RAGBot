import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def voice_service():
    with patch("app.services.voice_service.whisper"), \
         patch("app.services.voice_service.torch"), \
         patch("app.services.voice_service.aioredis.from_url") as mock_redis_from_url:
        mock_redis = AsyncMock()
        mock_redis_from_url.return_value = mock_redis
        from app.services.voice_service import VoiceService
        service = VoiceService()
        service.model = MagicMock()
        service.redis = mock_redis # Ensure the service uses the mocked redis
        return service

@pytest.mark.asyncio
async def test_initialize(voice_service):
    # Mock run_in_executor to prevent actual model loading
    with patch("asyncio.get_event_loop") as mock_get_event_loop:
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock()
        mock_get_event_loop.return_value = mock_loop
        
        voice_service.model = None # Reset model to test initialization
        await voice_service.initialize()
        
        assert voice_service.model is not None
        assert hasattr(voice_service, "device")
        mock_loop.run_in_executor.assert_awaited_once() # Ensure executor was called

@pytest.mark.asyncio
async def test_health_check_healthy(voice_service):
    voice_service.model = MagicMock()
    voice_service.redis.ping = AsyncMock(return_value=True)
    result = await voice_service.health_check()
    assert result["status"] == "healthy"
    assert result["model_loaded"] is True
    assert result["storage_type"] == "redis"

@pytest.mark.asyncio
async def test_health_check_unhealthy():
    with patch("app.services.voice_service.whisper"), \
         patch("app.services.voice_service.torch"), \
         patch("app.services.voice_service.aioredis.from_url") as mock_redis_from_url:
        mock_redis = AsyncMock()
        mock_redis_from_url.return_value = mock_redis
        mock_redis.ping.side_effect = Exception("Redis down")
        from app.services.voice_service import VoiceService
        service = VoiceService()
        service.model = None
        service.redis = mock_redis
        result = await service.health_check()
        assert result["status"] == "unhealthy"
        assert result["model_loaded"] is False
        assert "Redis down" in result["error"]

@pytest.mark.asyncio
async def test_transcribe_audio_success(voice_service):
    voice_service.model.transcribe.return_value = {
        "text": "hello",
        "confidence": 0.9,
        "segments": [{"avg_logprob": -0.1, "end": 1.0, "start": 0.0}]
    }
    audio_data = b"fake audio"
    from app.models.voice import AudioFile, VoiceSettings
    audio_file = AudioFile(filename="test.wav", content_type="audio/wav", size_bytes=len(audio_data))
    voice_settings = VoiceSettings(model="base", language="en")

    with patch("app.services.voice_service.AudioSegment.from_file", return_value=MagicMock(export=MagicMock(), set_frame_rate=MagicMock(return_value=MagicMock(set_channels=MagicMock())))), \
         patch("app.services.voice_service.tempfile.NamedTemporaryFile", MagicMock(return_value=MagicMock(name="temp.wav", __enter__=MagicMock(return_value=MagicMock(name="temp.wav")), __exit__=MagicMock()))), \
         patch("app.services.voice_service.os.unlink", MagicMock()):
        
        voice_service.redis.setex = AsyncMock()
        voice_service.redis.get = AsyncMock(return_value=None) # No initial status

        result = await voice_service.transcribe_audio(audio_data, audio_file, voice_settings)
    
    assert result.text == "hello"
    assert result.confidence is not None
    voice_service.redis.setex.assert_called()

@pytest.mark.asyncio
async def test_transcribe_audio_error(voice_service):
    voice_service.model.transcribe.side_effect = Exception("fail")
    audio_data = b"fake audio"
    from app.models.voice import AudioFile
    audio_file = AudioFile(filename="test.wav", content_type="audio/wav", size_bytes=len(audio_data))
    
    with patch("app.services.voice_service.AudioSegment.from_file", return_value=MagicMock(export=MagicMock(), set_frame_rate=MagicMock(return_value=MagicMock(set_channels=MagicMock())))), \
         patch("app.services.voice_service.tempfile.NamedTemporaryFile", MagicMock(return_value=MagicMock(name="temp.wav", __enter__=MagicMock(return_value=MagicMock(name="temp.wav")), __exit__=MagicMock()))), \
         patch("app.services.voice_service.os.unlink", MagicMock()):

        voice_service.redis.setex = AsyncMock()
        voice_service.redis.get = AsyncMock(return_value=None)

        with pytest.raises(Exception):
            await voice_service.transcribe_audio(audio_data, audio_file)
        voice_service.redis.setex.assert_called()

@pytest.mark.asyncio
async def test_validate_audio_valid(voice_service):
    # Mock AudioSegment.from_file
    with patch("app.services.voice_service.AudioSegment.from_file", return_value=MagicMock(__len__=MagicMock(return_value=1000))):
        audio_data = b"fake audio"
        result = await voice_service.validate_audio(audio_data, "audio/wav")
        assert result is True

@pytest.mark.asyncio
async def test_validate_audio_too_large(voice_service):
    audio_data = b"x" * (26 * 1024 * 1024)  # 26MB
    result = await voice_service.validate_audio(audio_data, "audio/wav")
    assert result is False

@pytest.mark.asyncio
async def test_validate_audio_invalid_format(voice_service):
    audio_data = b"fake audio"
    result = await voice_service.validate_audio(audio_data, "audio/unknown")
    assert result is False

@pytest.mark.asyncio
async def test_validate_audio_too_long(voice_service):
    with patch("app.services.voice_service.AudioSegment.from_file", return_value=MagicMock(__len__=MagicMock(return_value=1000 * 1000))): # 1000 seconds
        voice_service.settings.max_audio_duration = 10
        audio_data = b"fake audio"
        result = await voice_service.validate_audio(audio_data, "audio/wav")
        assert result is False

@pytest.mark.asyncio
async def test__convert_audio_success(voice_service):
    audio_data = b"fake_mp3_data"
    from app.models.voice import AudioFile
    audio_file = AudioFile(filename="test.mp3", content_type="audio/mp3", size_bytes=len(audio_data))

    mock_audio_segment = MagicMock()
    mock_audio_segment.set_frame_rate.return_value = mock_audio_segment
    mock_audio_segment.set_channels.return_value = mock_audio_segment

    with patch("app.services.voice_service.AudioSegment.from_file", return_value=mock_audio_segment):
        result = await voice_service._convert_audio(audio_data, audio_file)
        assert result == mock_audio_segment
        mock_audio_segment.set_frame_rate.assert_called_once_with(voice_service.settings.audio_sample_rate)
        mock_audio_segment.set_channels.assert_called_once_with(voice_service.settings.audio_channels)

@pytest.mark.asyncio
async def test__convert_audio_error(voice_service):
    audio_data = b"invalid_data"
    from app.models.voice import AudioFile
    audio_file = AudioFile(filename="test.mp3", content_type="audio/mp3", size_bytes=len(audio_data))

    with patch("app.services.voice_service.AudioSegment.from_file", side_effect=Exception("Conversion error")):
        with pytest.raises(ValueError, match="Failed to process audio"):
            await voice_service._convert_audio(audio_data, audio_file)

@pytest.mark.asyncio
async def test__calculate_confidence_with_segments(voice_service):
    whisper_result = {
        "segments": [
            {"avg_logprob": -0.1, "start": 0.0, "end": 1.0},
            {"avg_logprob": -0.2, "start": 1.0, "end": 2.0}
        ]
    }
    confidence = voice_service._calculate_confidence(whisper_result)
    # Expected: (0.9 * 1.0 + 0.8 * 1.0) / 2.0 = 0.85
    assert confidence == pytest.approx(0.85)

@pytest.mark.asyncio
async def test__calculate_confidence_no_segments(voice_service):
    whisper_result = {}
    confidence = voice_service._calculate_confidence(whisper_result)
    assert confidence is None

@pytest.mark.asyncio
async def test__calculate_confidence_empty_segments(voice_service):
    whisper_result = {"segments": []}
    confidence = voice_service._calculate_confidence(whisper_result)
    assert confidence is None

@pytest.mark.asyncio
async def test__update_status_and_get_processing_status(voice_service):
    from app.models.voice import AudioProcessingStatus
    audio_id = "test_audio_id"

    # Test initial status update
    voice_service.redis.setex = AsyncMock()
    voice_service.redis.get = AsyncMock(return_value=None)
    await voice_service._update_status(audio_id, "processing", 25)
    voice_service.redis.setex.assert_called_once()
    
    # Test status retrieval
    mock_status_data = AudioProcessingStatus(audio_id=audio_id, status="processing", progress=25, started_at=time.time()).json()
    voice_service.redis.get.return_value = mock_status_data
    status = await voice_service.get_processing_status(audio_id)
    assert status.audio_id == audio_id
    assert status.status == "processing"
    assert status.progress == 25

    # Test status update to completed
    voice_service.redis.setex.reset_mock()
    voice_service.redis.get.return_value = mock_status_data # Return previous status for started_at
    await voice_service._update_status(audio_id, "completed", 100)
    voice_service.redis.setex.assert_called_once()
    updated_status_data = voice_service.redis.setex.call_args[0][2] # Get the JSON string passed to setex
    updated_status = AudioProcessingStatus.parse_raw(updated_status_data)
    assert updated_status.status == "completed"
    assert updated_status.progress == 100
    assert updated_status.completed_at is not None
    assert updated_status.processing_time is not None

@pytest.mark.asyncio
async def test_cleanup(voice_service):
    voice_service.model = MagicMock()
    voice_service.redis.close = AsyncMock() # Mock redis close
    with patch("torch.cuda.is_available", return_value=True), \
         patch("torch.cuda.empty_cache", MagicMock()) as mock_empty_cache:
        await voice_service.cleanup()
        assert voice_service.model is None
        mock_empty_cache.assert_called_once()
    voice_service.redis.close.assert_awaited_once()

@pytest.mark.asyncio
@pytest.mark.parametrize("content_type, expected_result", [
    ("audio/wav", True),
    ("audio/mp3", True),
    ("audio/mp4", True),
    ("audio/m4a", True),
    ("audio/ogg", True),
    ("audio/webm", True), # Added webm
    ("audio/unknown", False),
    ("image/png", False),
])
async def test_validate_audio_formats(voice_service, content_type, expected_result):
    with patch("app.services.voice_service.AudioSegment.from_file", return_value=MagicMock(__len__=MagicMock(return_value=1000))):
        audio_data = b"fake audio"
        result = await voice_service.validate_audio(audio_data, content_type)
        assert result is expected_result
