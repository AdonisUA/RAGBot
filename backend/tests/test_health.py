"""
Tests for health check endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client


def test_basic_health_check(test_client):
    """Test basic health check endpoint"""
    response = test_client.get("/health/")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "AI ChatBot"
    assert data["version"] == "1.0.0"


def test_liveness_check(test_client):
    """Test liveness probe endpoint"""
    response = test_client.get("/health/liveness")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "alive"
    assert "timestamp" in data
    assert "uptime" in data


def test_readiness_check(test_client, monkeypatch):
    """Test readiness probe endpoint"""
    # Mock get_settings to control API key configuration
    mock_settings = MagicMock()
    mock_settings.openai_api_key = "test_key"
    monkeypatch.setattr("app.core.config.get_settings", lambda: mock_settings)

    response = test_client.get("/health/readiness")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ready"
    assert "timestamp" in data


def test_readiness_check_unhealthy_api_key(test_client, monkeypatch):
    """Test readiness probe endpoint when API key is not configured"""
    mock_settings = MagicMock()
    mock_settings.openai_api_key = ""
    monkeypatch.setattr("app.core.config.get_settings", lambda: mock_settings)

    response = test_client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_ready"
    assert "reason" in data
    assert "API key not configured" in data["reason"]


def test_system_info(test_client):
    """Test system info endpoint"""
    response = test_client.get("/health/system")

    assert response.status_code == 200
    data = response.json()

    assert "platform" in data
    assert "python_version" in data
    assert "cpu_count" in data


def test_metrics(test_client):
    """Test metrics endpoint"""
    response = test_client.get("/health/metrics")

    assert response.status_code == 200
    data = response.json()

    assert "timestamp" in data
    assert "system" in data
    assert "process" in data
    assert "cpu_percent" in data["system"]
    assert "memory_total" in data["system"]

@pytest.mark.asyncio
async def test_detailed_health_check_all_healthy(test_client, monkeypatch):
    """Test detailed health check when all services are healthy"""
    # Mock service health checks
    mock_ai_service = AsyncMock()
    mock_ai_service.health_check.return_value = {"status": "healthy"}
    mock_voice_service = AsyncMock()
    mock_voice_service.health_check.return_value = {"status": "healthy"}
    mock_memory_service = AsyncMock()
    mock_memory_service.health_check.return_value = {"status": "healthy"}
    mock_vector_memory_service = AsyncMock()
    mock_vector_memory_service.health_check.return_value = {"status": "healthy"}

    monkeypatch.setattr("app.services.ai_service.AIService", lambda: mock_ai_service)
    monkeypatch.setattr("app.services.voice_service.VoiceService", lambda: mock_voice_service)
    monkeypatch.setattr("app.services.memory_service.MemoryService", lambda: mock_memory_service)
    monkeypatch.setattr("app.services.vector_memory_service.VectorMemoryService", lambda: mock_vector_memory_service)

    response = test_client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["ai_service"]["status"] == "healthy"
    assert data["services"]["voice_service"]["status"] == "healthy"
    assert data["services"]["memory_service"]["status"] == "healthy"
    assert data["services"]["vector_memory_service"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_detailed_health_check_some_unhealthy(test_client, monkeypatch):
    """Test detailed health check when some services are unhealthy"""
    mock_ai_service = AsyncMock()
    mock_ai_service.health_check.return_value = {"status": "healthy"}
    mock_voice_service = AsyncMock()
    mock_voice_service.health_check.return_value = {"status": "unhealthy", "error": "Voice fail"}
    mock_memory_service = AsyncMock()
    mock_memory_service.health_check.return_value = {"status": "healthy"}
    mock_vector_memory_service = AsyncMock()
    mock_vector_memory_service.health_check.return_value = {"status": "unhealthy", "error": "Vector fail"}

    monkeypatch.setattr("app.services.ai_service.AIService", lambda: mock_ai_service)
    monkeypatch.setattr("app.services.voice_service.VoiceService", lambda: mock_voice_service)
    monkeypatch.setattr("app.services.memory_service.MemoryService", lambda: mock_memory_service)
    monkeypatch.setattr("app.services.vector_memory_service.VectorMemoryService", lambda: mock_vector_memory_service)

    response = test_client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["ai_service"]["status"] == "healthy"
    assert data["services"]["voice_service"]["status"] == "unhealthy"
    assert data["services"]["vector_memory_service"]["status"] == "unhealthy"


def test_readiness_check_unhealthy_memory_service(test_client, monkeypatch):
    """Test readiness probe endpoint when memory service is unhealthy"""
    mock_settings = MagicMock()
    mock_settings.openai_api_key = "test_key"
    monkeypatch.setattr("app.core.config.get_settings", lambda: mock_settings)

    mock_memory_service = AsyncMock()
    mock_memory_service.health_check.return_value = {"status": "unhealthy", "error": "Memory fail"}
    monkeypatch.setattr("app.main.app.state", "memory_service", mock_memory_service)

    response = test_client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_ready"
    assert "reason" in data
    assert "Memory fail" in data["reason"]


def test_readiness_check_unhealthy_chromadb_service(test_client, monkeypatch):
    """Test readiness probe endpoint when ChromaDB service is unhealthy"""
    mock_settings = MagicMock()
    mock_settings.openai_api_key = "test_key"
    monkeypatch.setattr("app.core.config.get_settings", lambda: mock_settings)

    mock_vector_memory_service = AsyncMock()
    mock_vector_memory_service.health_check.return_value = {"status": "unhealthy", "error": "ChromaDB fail"}
    monkeypatch.setattr("app.main.app.state", "vector_memory_service", mock_vector_memory_service)

    response = test_client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_ready"
    assert "reason" in data
    assert "ChromaDB fail" in data["reason"]
