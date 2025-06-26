import structlog
from typing import Optional
from app.utils.prompts import PromptManager

logger = structlog.get_logger()

# Импорт для celery worker
try:
    from app.worker import research_and_learn
except ImportError:
    research_and_learn = None

class ResearchService:
    def __init__(self):
        self.prompt_manager = PromptManager()

    async def start_research_for_session(self, session_id: str, query: str):
        if research_and_learn is None:
            logger.warning("Celery worker not available, research_and_learn not imported")
            return
        logger.info("Triggering research_and_learn Celery task (manual)", question=query, session_id=session_id)
        research_and_learn.delay(query)

    async def trigger_research_if_needed(self, user_message: str, ai_response: str, session_id: Optional[str] = None):
        """Вызвать Celery-агента, если AI не знает ответ или явно не может помочь"""
        if research_and_learn is None:
            logger.warning("Celery worker not available, research_and_learn not imported")
            return
        triggers = self.prompt_manager.prompts.get("research_triggers", [])
        response_lower = ai_response.lower()
        if any(trigger.lower() in response_lower for trigger in triggers):
            logger.info("Triggering research_and_learn Celery task", question=user_message, session_id=session_id)
            research_and_learn.delay(user_message)
