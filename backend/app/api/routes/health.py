

"""
Health check endpoints for AI ChatBot
System status and monitoring endpoints
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import structlog
import time
import psutil
import platform
from datetime import datetime

from app.core.config import get_settings
from app.services.ai_service import AIService
from app.services.voice_service import VoiceService
from app.services.memory_service import MemoryService
from app.services.vector_memory_service import VectorMemoryService

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AI ChatBot",
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with service status"""

    start_time = time.time()
    settings = get_settings()

    # Initialize services
    ai_service = AIService()
    voice_service = VoiceService()
    memory_service = MemoryService()
    vector_service = VectorMemoryService()

    # Check each service
    services_status = {}

    # AI Service
    try:
        ai_health = await ai_service.health_check()
        services_status["ai_service"] = ai_health
    except Exception as e:
        services_status["ai_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Voice Service
    try:
        voice_health = await voice_service.health_check()
        services_status["voice_service"] = voice_health
    except Exception as e:
        services_status["voice_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Memory Service (Redis/JSON)
    try:
        mem_health = await memory_service.health_check()
        services_status["memory_service"] = mem_health
    except Exception as e:
        services_status["memory_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Vector DB (ChromaDB)
    try:
        chroma_health = await vector_service.health_check()
        services_status["vector_memory_service"] = chroma_health
    except Exception as e:
        services_status["vector_memory_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Overall status
    all_healthy = all(
        service.get("status") == "healthy"
        for service in services_status.values()
    )

    response_time = time.time() - start_time

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "response_time": response_time,
        "services": services_status,
        "system": await get_system_info(),
        "configuration": {
            "debug_mode": settings.debug,
            "log_level": settings.log_level,
            "memory_type": settings.memory_type,
            "voice_enabled": settings.voice_enabled
        }
    }


@router.get("/system")
async def system_info() -> Dict[str, Any]:
    """System information endpoint"""

    return await get_system_info()


@router.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """Basic metrics endpoint"""

    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Get process metrics
    process = psutil.Process()
    process_memory = process.memory_info()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "cpu_percent": cpu_percent,
            "memory_total": memory.total,
            "memory_available": memory.available,
            "memory_percent": memory.percent,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "disk_percent": (disk.used / disk.total) * 100
        },
        "process": {
            "memory_rss": process_memory.rss,
            "memory_vms": process_memory.vms,
            "cpu_percent": process.cpu_percent(),
            "num_threads": process.num_threads(),
            "create_time": process.create_time()
        }
    }


@router.get("/readiness")
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes readiness probe endpoint"""

    try:
        # Check if services can handle requests
        settings = get_settings()

        # Basic configuration check
        if not settings.openai_api_key or settings.openai_api_key == "your-openai-api-key-here":
            return {
                "status": "not_ready",
                "reason": "OpenAI API key not configured"
            }

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {
            "status": "not_ready",
            "reason": str(e)
        }


@router.get("/liveness")
async def liveness_check() -> Dict[str, Any]:
    """Kubernetes liveness probe endpoint"""

    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time() - psutil.Process().create_time()
    }


async def get_system_info() -> Dict[str, Any]:
    """Get system information"""

    try:
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "boot_time": psutil.boot_time()
        }
    except Exception as e:
        logger.warning("Failed to get system info", error=str(e))
        return {"error": "Failed to retrieve system information"}
