📖 AI ChatBot - Руководство разработчика
Этот гайд содержит всю необходимую информацию для локальной разработки, тестирования и внесения изменений в проект.

1. Настройка локального окружения
1.1. Пререквизиты
Docker и Docker Compose (рекомендуется для полного стека)

Node.js (v18+) и npm

Python (v3.9+) и pip

virtualenv для изоляции зависимостей

1.2. Backend
cd backend

# Создать и активировать виртуальное окружение
python -m venv venv
source venv/bin/activate # для Linux/macOS
# venv\Scripts\activate # для Windows

# Установить зависимости
pip install -r requirements.txt
# Для разработки:
pip install -r requirements-dev.txt

# Скопировать .env и заполнить ключи
cp ../config/.env.template ../.env
nano ../.env

1.3. Frontend
cd frontend

# Установить зависимости
npm install

2. Запуск в режиме разработки
2.1. С помощью Docker (Рекомендуемый способ)
Docker Compose настроен для hot-reload. Изменения в коде backend и frontend будут автоматически применяться внутри контейнеров без необходимости их перезапуска.

# Запустить все сервисы (backend, frontend, redis, chromadb, celery)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

2.2. Локально (без Docker)
Этот способ полезен для более детальной отладки конкретного сервиса. Запустите каждый сервис в отдельном терминале.

# Терминал 1: Redis
redis-server
# Терминал 2: ChromaDB (опционально, если используется RAG)
# см. инструкции в docs/ARCHITECTURE.md
# Терминал 3: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Терминал 4: Celery worker (если используется)
celery -A app.worker.celery_app worker --loglevel=info
# Терминал 5: Frontend
cd frontend
npm start

3. Тестирование
3.1. Backend тесты
Мы используем pytest для unit и integration-тестов.

cd backend
source venv/bin/activate

# Запустить все тесты в verbose-режиме
pytest -v

# Запустить тесты с генерацией отчета о покрытии кода
pytest --cov=app

4. Стиль кода и Качество
Для поддержания единого стиля кода и предотвращения простых ошибок, пожалуйста, используйте линтеры перед коммитом.

4.1. Backend (Python)
Форматирование: black

Линтинг: flake8

cd backend
black . && flake8 .

4.2. Frontend (TypeScript/React)
Форматирование: prettier

Линтинг: eslint

cd frontend
npm run format && npm run lint

5. Особенности архитектуры и внедрение зависимостей
- Все сервисы используют DI (dependency injection) через FastAPI.
- AIService использует ленивую инициализацию провайдеров.
- VectorMemoryService реализован как Singleton.
- Статус обработки аудио в VoiceService хранится в Redis.
- Nginx — опциональный компонент, используется только в продакшене.

6. Как добавить нового AI-провайдера
Создать файл провайдера: В backend/app/services/ai_providers/ создайте файл my_provider.py.

Реализовать класс, унаследовав его от BaseAIProvider и реализовав все его абстрактные методы (generate_response, generate_streaming_response и т.д.).

from .base import BaseAIProvider

class MyProvider(BaseAIProvider):
    async def generate_response(self, ...):
        # Ваша логика запроса к API нового провайдера
        pass
    # ... остальные методы

Зарегистрировать провайдер: В backend/app/services/ai_service.py импортируйте ваш новый класс и добавьте его в логику инициализации в методе _initialize_providers.

# В методе _initialize_providers() класса AIService
if self.settings.my_provider_api_key:
    self.providers["my_provider_name"] = MyProvider(...)

Добавить конфигурацию: Добавьте необходимые переменные (например, MY_PROVIDER_API_KEY) в backend/app/core/config.py и в файл-шаблон config/.env.template.

Готово! После перезапуска, ваш провайдер будет автоматически обнаружен и доступен для выбора в системе.
