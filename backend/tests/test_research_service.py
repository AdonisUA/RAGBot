import pytest
from unittest.mock import patch, MagicMock
from app.services.research_service import ResearchService

@pytest.mark.asyncio
async def test_start_research_for_session_triggers_celery():
    with patch("app.services.research_service.research_and_learn") as mock_task:
        service = ResearchService()
        await service.start_research_for_session("session1", "test query")
        mock_task.delay.assert_called_once_with("test query")

@pytest.mark.asyncio
async def test_start_research_for_session_no_celery():
    with patch("app.services.research_service.research_and_learn", None):
        service = ResearchService()
        # Не должно быть исключения, просто return
        await service.start_research_for_session("session1", "test query")

@pytest.mark.asyncio
@pytest.mark.parametrize("ai_response", [
    "я не знаю",
    "не могу помочь",
    "не могу ответить",
    "I don't know",
    "cannot help",
    "don't know",
    "I really don't know anything about that.", # Test with more context
    "Sorry, I cannot help you with that."
])
async def test_trigger_research_if_needed_triggers_on_trigger_phrase(ai_response):
    with patch("app.services.research_service.research_and_learn") as mock_task:
        service = ResearchService()
        user_question = "user question"
        session_id = "session1"
        await service.trigger_research_if_needed(user_question, ai_response, session_id)
        mock_task.delay.assert_called_once_with(user_question)

@pytest.mark.asyncio
async def test_trigger_research_if_needed_not_triggered():
    with patch("app.services.research_service.research_and_learn") as mock_task:
        service = ResearchService()
        await service.trigger_research_if_needed("user question", "Here is your answer", "session1")
        mock_task.delay.assert_not_called()

@pytest.mark.asyncio
async def test_start_research_for_session_no_celery_logs_warning(caplog):
    with patch("app.services.research_service.research_and_learn", None):
        service = ResearchService()
        with caplog.at_level(logging.WARNING):
            await service.start_research_for_session("session1", "test query")
            assert "Celery worker not available, research_and_learn not imported" in caplog.text

@pytest.mark.asyncio
async def test_trigger_research_if_needed_no_celery_logs_warning(caplog):
    with patch("app.services.research_service.research_and_learn", None):
        service = ResearchService()
        with caplog.at_level(logging.WARNING):
            await service.trigger_research_if_needed("user question", "I don't know", "session1")
            assert "Celery worker not available, research_and_learn not imported" in caplog.text

