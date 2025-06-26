from celery import Celery
import structlog
import asyncio
from app.services.vector_memory_service import VectorMemoryService
from app.services.ai_providers.openai_provider import OpenAIProvider
from app.models.chat import Message, ChatSettings
import os
from app.core.logging import setup_logging
from app.core.config import get_settings

settings = get_settings()
setup_logging(settings.log_level)

logger = structlog.get_logger()

celery_app = Celery(
    'worker',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

SERPAPI_KEY = os.environ.get('SERPAPI_KEY')

async def serpapi_search(query: str) -> str:
    # TODO: Реализовать реальный вызов SerpAPI
    # Сейчас просто возвращаем заглушку
    logger.info("SerpAPI search (stub)", query=query)
    return f"[SerpAPI results for: {query}]"

async def generate_faq_with_openai(question: str, context: str) -> str:
    # Используем OpenAIProvider напрямую
    openai_provider = OpenAIProvider({})
    system_prompt = (
        "Ты — AI-ассистент, который помогает искать и формулировать справки по сложным вопросам. "
        "Используй предоставленный контекст из поиска, чтобы дать максимально точный и полезный ответ. "
        "Если контекст не содержит ответа, честно укажи это."
    )
    chat_settings = ChatSettings(system_prompt=system_prompt)
    messages = [
        Message(content=f"Контекст поиска: {context}", role="system", session_id="faq"),
        Message(content=question, role="user", session_id="faq")
    ]
    answer = await openai_provider.generate_response(
        question,
        messages,
        settings=chat_settings,
        stream=False
    )
    return answer

@celery_app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5},
    retry_backoff=True
)
def research_and_learn(question: str):
    logger.info("Celery task research_and_learn started", question=question)
    loop = asyncio.get_event_loop()
    try:
        # 1. Поиск через SerpAPI (или заглушка)
        context = loop.run_until_complete(serpapi_search(question))
        # 2. Генерация справки через OpenAIProvider
        answer = loop.run_until_complete(generate_faq_with_openai(question, context))
        # 3. Сохранение в VectorMemoryService
        vector_memory = VectorMemoryService()
        loop.run_until_complete(vector_memory.add_document(answer, metadata={
            "source": "research_agent",
            "question": question
        }))
        logger.info("Research answer saved to vector memory", question=question)
        return {"status": "done", "question": question, "answer": answer}
    except Exception as e:
        logger.error("Error in research_and_learn", error=str(e), question=question)
        return {"status": "error", "error": str(e), "question": question}
