

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import structlog
from typing import List

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import chat
from app.api.routes import voice
from app.api.routes import config
from app.api.routes import health
from app.utils.prompts import PromptManager
from app.services.websocket_manager import WebSocketManager
from app.core.exceptions import setup_exception_handlers

settings = get_settings()
setup_logging(settings.log_level)
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI ChatBot Backend", version="1.0.0")
    app.state.websocket_manager = WebSocketManager()
    await app.state.websocket_manager.start()
    try:
        if settings.whisper_preload:
            from app.services.voice_service import VoiceService
            voice_service = VoiceService()
            await voice_service.initialize()
            app.state.voice_service = voice_service
            logger.info("Whisper model preloaded")
    except Exception as e:
        logger.warning("Failed to preload Whisper model", error=str(e))
    yield
    logger.info("Shutting down AI ChatBot Backend")
    if hasattr(app.state, 'voice_service'):
        await app.state.voice_service.cleanup()
    await app.state.websocket_manager.stop()

app = FastAPI(
    title="AI ChatBot API",
    description="Universal AI ChatBot with voice input and memory",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )

setup_exception_handlers(app)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

@app.get("/")
async def root():
    return {
        "message": "AI ChatBot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled"
    }

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    manager: WebSocketManager = app.state.websocket_manager
    await manager.connect(websocket)
    logger.info("WebSocket client connected", client_id=id(websocket))
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected", client_id=id(websocket))
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), client_id=id(websocket))
        await manager.send_error(websocket, "Internal server error")
        manager.disconnect(websocket)

@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    manager: WebSocketManager = app.state.websocket_manager
    await manager.connect(websocket)
    logger.info("Voice WebSocket client connected", client_id=id(websocket))
    try:
        while True:
            data = await websocket.receive_bytes()
            await manager.handle_voice_data(websocket, data)
    except WebSocketDisconnect:
        logger.info("Voice WebSocket client disconnected", client_id=id(websocket))
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("Voice WebSocket error", error=str(e), client_id=id(websocket))
        await manager.send_error(websocket, "Voice processing error")
        manager.disconnect(websocket)


