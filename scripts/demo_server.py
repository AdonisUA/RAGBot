#!/usr/bin/env python3
"""
Demo server for AI ChatBot
Simple FastAPI server to demonstrate the project
"""

import sys
import os
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import uvicorn
    from datetime import datetime
    import random
    import time
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Installing required packages...")
    os.system("pip install fastapi uvicorn pydantic")
    print("Please run the script again after installation.")
    sys.exit(1)

# Create FastAPI app
app = FastAPI(
    title="AI ChatBot Demo API",
    description="Demo version of AI ChatBot API",
    version="1.0.0-demo"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo data models
class ChatRequest(BaseModel):
    message: str
    session_id: str = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    message_id: str
    timestamp: str

# Demo responses
DEMO_RESPONSES = [
    "Привет! Я демо-версия AI чатбота. Как дела?",
    "Это отличный вопрос! В демо-режиме я могу показать, как работает интерфейс.",
    "Проект поддерживает OpenAI GPT, Google Gemini и Anthropic Claude!",
    "Голосовой ввод работает через Whisper для распознавания речи.",
    "Архитектура модульная - легко добавлять новые AI провайдеры.",
    "Docker развертывание позволяет запустить все одной командой!",
    "Это production-ready решение с мониторингом и логированием.",
]

# Routes
@app.get("/")
async def root():
    return {
        "message": "AI ChatBot Demo API",
        "version": "1.0.0-demo",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health/")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AI ChatBot Demo",
        "version": "1.0.0-demo"
    }

@app.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "ai_service": {"status": "healthy", "provider": "demo"},
            "voice_service": {"status": "healthy", "model": "demo"},
            "memory_service": {"status": "healthy", "storage_type": "demo"}
        },
        "demo_mode": True
    }

@app.post("/api/chat/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    # Simulate processing time
    await asyncio.sleep(random.uniform(0.5, 2.0))

    session_id = request.session_id or f"demo_session_{int(time.time())}"

    # Select random demo response
    response_text = random.choice(DEMO_RESPONSES)

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        message_id=f"msg_{int(time.time())}_{random.randint(1000, 9999)}",
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/api/chat/providers")
async def get_providers():
    return {
        "current_provider": "demo",
        "available_providers": ["demo", "openai", "gemini"],
        "provider_configs": {
            "demo": {"name": "demo", "model": "demo-model"},
            "openai": {"name": "openai", "model": "gpt-3.5-turbo"},
            "gemini": {"name": "gemini", "model": "gemini-pro"}
        }
    }

@app.post("/api/chat/providers/switch")
async def switch_provider(provider: str):
    return {
        "message": f"Switched to provider: {provider} (demo mode)",
        "current_provider": provider
    }

@app.get("/api/chat/models")
async def get_models():
    return {
        "providers": {
            "demo": ["demo-model"],
            "openai": ["gpt-3.5-turbo", "gpt-4"],
            "gemini": ["gemini-pro"]
        }
    }

# Import asyncio after FastAPI setup
import asyncio

if __name__ == "__main__":
    print("🤖 AI ChatBot Demo Server")
    print("=" * 40)
    print("Starting demo server...")
    print("Frontend: http://localhost:3000 (if available)")
    print("Backend API: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 40)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
