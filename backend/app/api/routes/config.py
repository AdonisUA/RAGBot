

"""
Configuration API endpoints for AI ChatBot
Handles runtime configuration management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import structlog
import json
from pathlib import Path

from app.core.config import get_settings
from app.models.chat import ChatSettings
from app.models.voice import VoiceSettings
from app.utils.prompts import PromptManager

logger = structlog.get_logger()
router = APIRouter()


def get_prompt_manager() -> PromptManager:
    """Dependency to get prompt manager instance"""
    return PromptManager()


@router.get("/")
async def get_configuration() -> Dict[str, Any]:
    """Get current configuration"""

    settings = get_settings()

    # Return safe configuration (no secrets)
    config = {
        "ai": {
            "model": settings.openai_model,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "frequency_penalty": settings.frequency_penalty,
            "presence_penalty": settings.presence_penalty
        },
        "voice": {
            "model": settings.whisper_model,
            "enabled": settings.voice_enabled,
            "auto_send": settings.auto_send_after_transcription,
            "max_duration": settings.max_audio_duration,
            "sample_rate": settings.audio_sample_rate,
            "channels": settings.audio_channels
        },
        "memory": {
            "type": settings.memory_type,
            "max_history": settings.max_history_messages,
            "auto_save": settings.auto_save
        },
        "server": {
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug,
            "log_level": settings.log_level
        },
        "features": {
            "voice_output": settings.feature_voice_output,
            "file_upload": settings.feature_file_upload,
            "multi_language": settings.feature_multi_language,
            "streaming_responses": settings.beta_streaming_responses,
            "conversation_search": settings.beta_conversation_search
        }
    }

    return config


@router.get("/chat", response_model=ChatSettings)
async def get_chat_settings() -> ChatSettings:
    """Get chat-specific settings"""

    settings = get_settings()

    return ChatSettings(
        model=settings.openai_model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        frequency_penalty=settings.frequency_penalty,
        presence_penalty=settings.presence_penalty,
        context_window=settings.max_history_messages
    )


@router.post("/chat", response_model=ChatSettings)
async def update_chat_settings(
    chat_settings: ChatSettings
) -> ChatSettings:
    """Update chat settings"""

    settings = get_settings()
    # Update relevant settings fields
    settings.openai_model = chat_settings.model
    settings.temperature = chat_settings.temperature
    settings.max_tokens = chat_settings.max_tokens
    settings.top_p = chat_settings.top_p
    settings.frequency_penalty = chat_settings.frequency_penalty
    settings.presence_penalty = chat_settings.presence_penalty
    settings.context_window = chat_settings.context_window

    # Save updated settings to file
    settings.save_to_file(str(Path(settings.config_path) / "settings.json"))

    logger.info("Chat settings updated", settings=chat_settings.dict())

    return chat_settings


@router.get("/voice", response_model=VoiceSettings)
async def get_voice_settings() -> VoiceSettings:
    """Get voice-specific settings"""

    settings = get_settings()

    return VoiceSettings(
        model=settings.whisper_model,
        language="auto",  # Default
        task="transcribe"
    )


@router.post("/voice", response_model=VoiceSettings)
async def update_voice_settings(
    voice_settings: VoiceSettings
) -> VoiceSettings:
    """Update voice settings"""

    settings = get_settings()
    # Update relevant settings fields
    settings.whisper_model = voice_settings.model
    settings.audio_format = "wav" # Assuming wav for now, can be made configurable
    settings.max_audio_duration = 60 # Assuming 60s for now, can be made configurable
    settings.audio_sample_rate = 16000 # Assuming 16kHz for now, can be made configurable
    settings.audio_channels = 1 # Assuming 1 channel for now, can be made configurable
    settings.voice_enabled = True # Assuming voice is enabled when settings are updated
    settings.auto_send_after_transcription = voice_settings.auto_send # Assuming auto_send is part of VoiceSettings

    # Save updated settings to file
    settings.save_to_file(str(Path(settings.config_path) / "settings.json"))

    logger.info("Voice settings updated", settings=voice_settings.dict())

    return voice_settings


@router.get("/flows")
async def get_flow_configuration() -> Dict[str, Any]:
    """Get flow configuration from flows.json"""

    try:
        settings = get_settings()
        flows_file = Path(settings.config_path) / "flows.json"

        if flows_file.exists():
            with open(flows_file, 'r', encoding='utf-8') as f:
                flows = json.load(f)

            logger.info("Flow configuration retrieved")
            return flows
        else:
            logger.warning("Flows configuration file not found")
            return {"error": "Flows configuration not found"}

    except Exception as e:
        logger.error("Failed to load flows configuration", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to load configuration")


@router.post("/flows")
async def update_flow_configuration(
    flows: Dict[str, Any]
) -> Dict[str, Any]:
    """Update flow configuration"""

    try:
        settings = get_settings()
        flows_file = Path(settings.config_path) / "flows.json"

        # Validate flows structure (basic validation)
        required_sections = ["chat_flow", "voice_flow", "memory_flow", "ui_flow"]
        for section in required_sections:
            if section not in flows:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required section: {section}"
                )

        # Save flows configuration
        flows_file.parent.mkdir(parents=True, exist_ok=True)
        with open(flows_file, 'w', encoding='utf-8') as f:
            json.dump(flows, f, indent=2, ensure_ascii=False)

        logger.info("Flow configuration updated")

        return {"message": "Flow configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update flows configuration", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.get("/prompts")
async def get_prompts(
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> Dict[str, Any]:
    """Get prompt templates"""

    try:
        # Return current prompts
        return prompt_manager.prompts

    except Exception as e:
        logger.error("Failed to get prompts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get prompts")


@router.post("/prompts")
async def update_prompts(
    prompts: Dict[str, Any],
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> Dict[str, Any]:
    """Update prompt templates"""

    try:
        settings = get_settings()
        prompts_file = Path(settings.config_path) / "prompts.json"

        # Validate prompts structure
        validation_result = prompt_manager.validate_prompt_config()
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid prompt configuration: {validation_result['errors']}"
            )

        # Save prompts
        prompts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(prompts_file, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)

        # Reload prompts
        prompt_manager.reload_prompts()

        logger.info("Prompts updated")

        return {"message": "Prompts updated successfully"}

    except Exception as e:
        logger.error("Failed to update prompts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update prompts")


@router.post("/prompts/reload")
async def reload_prompts(
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> Dict[str, Any]:
    """Reload prompts from file"""

    try:
        prompt_manager.reload_prompts()

        logger.info("Prompts reloaded")

        return {"message": "Prompts reloaded successfully"}

    except Exception as e:
        logger.error("Failed to reload prompts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to reload prompts")


@router.get("/prompts/validate")
async def validate_prompts(
    prompt_manager: PromptManager = Depends(get_prompt_manager)
) -> Dict[str, Any]:
    """Validate prompt configuration"""

    try:
        validation_result = prompt_manager.validate_prompt_config()

        return validation_result

    except Exception as e:
        logger.error("Failed to validate prompts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to validate prompts")


@router.get("/environment")
async def get_environment_info() -> Dict[str, Any]:
    """Get environment information (safe values only)"""

    settings = get_settings()

    return {
        "debug_mode": settings.debug,
        "log_level": settings.log_level,
        "memory_type": settings.memory_type,
        "voice_enabled": settings.voice_enabled,
        "features": {
            "voice_output": settings.feature_voice_output,
            "file_upload": settings.feature_file_upload,
            "multi_language": settings.feature_multi_language,
            "custom_models": settings.feature_custom_models,
            "plugins": settings.feature_plugins
        },
        "beta_features": {
            "streaming_responses": settings.beta_streaming_responses,
            "conversation_search": settings.beta_conversation_search,
            "export_conversations": settings.beta_export_conversations
        }
    }


@router.get("/defaults")
async def get_default_configuration() -> Dict[str, Any]:
    """Get default configuration values"""

    return {
        "chat": {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000,
            "context_window": 10
        },
        "voice": {
            "model": "base",
            "language": "auto",
            "task": "transcribe",
            "auto_send": True
        },
        "memory": {
            "type": "json",
            "max_history": 50,
            "auto_save": True
        },
        "ui": {
            "theme": "auto",
            "animations": True,
            "auto_scroll": True
        }
    }
