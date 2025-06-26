# 🤖 AI ChatBot — Universal Platform for AI Agents

AI ChatBot — это production-ready open source фреймворк для создания интеллектуальных чат-агентов с поддержкой нескольких AI-провайдеров, голосового ввода и расширяемой памятью. Проект развивается по лучшим практикам: архитектурный аудит, инженерный контроль, покрытие тестами, прозрачная документация.

## ✨ Ключевые возможности
- **Мульти-провайдерность**: Поддержка OpenAI, Google Gemini, Anthropic с возможностью переключения "на лету".
- **Модульность**: Легко добавлять новых AI-провайдеров и плагины.
- **Голосовой ввод**: Высококачественная транскрипция речи через Whisper.
- **Real-Time**: Взаимодействие через WebSockets.
- **Расширенная память**: Векторная база (ChromaDB) для долгосрочного контекста.
- **Конфигурируемость**: Гибкая настройка через .env и JSON.
- **Контейнеризация**: Docker-инфраструктура для разработки и продакшена.
- **CI/CD**: Автоматизация тестов, линтинга, покрытия через GitHub Actions.

## 📝 Тестирование и качество кода
- Покрытие тестами всех ключевых сервисов, edge-cases, интеграций, ошибок.
- Изоляция тестов, моки, фикстуры, чистка данных.
- Подробный [TEST_REPORT.md](docs/TEST_REPORT.md) отражает текущее покрытие и стабильность.

**Запуск тестов (backend):**
```bash
cd backend && pytest
```

**Линтеры и форматтеры (backend):**
```bash
cd backend && black . && isort . && flake8 .
```

**Линтеры и форматтеры (frontend):**
```bash
cd frontend && npm run format && npm run lint
```

## 🚀 Быстрый старт
1. Клонировать репозиторий:
```bash
git clone https://github.com/your-org/ChatBot.git
cd ChatBot
```
2. Настроить окружение:
```bash
cp config/.env.template .env
# Добавьте хотя бы один API ключ (OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY)
```
3. Запустить проект:
```bash
./start.sh
```

**Доступные сервисы:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs

## 🏗️ Архитектура и документация
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — архитектура, компоненты, потоки данных
- [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) — настройка, разработка, тестирование
- [ROADMAP.md](docs/ROADMAP.md) — план развития
- [TEST_REPORT.md](docs/TEST_REPORT.md) — покрытие тестами
- [engineer_report.md](engineer_report.md) — инженерный отчёт о прогрессе
- [action_plan.md](action_plan.md) — стратегический аудит

## 📁 Структура проекта
ChatBot/
├── backend/         # FastAPI приложение
├── frontend/        # React приложение
├── config/          # Конфиги (.env, prompts.json)
├── data/            # Данные (JSON-сессии)
├── docs/            # Документация (рус/англ)
├── docker-compose.yml
└── start.sh         # Скрипт управления

> **Примечание:** Nginx — опциональный компонент, используется только в продакшене для reverse proxy и отдачи статики.

---
Проект готов к open source и production, развивается по best practices, открыт для коммьюнити и внешних контрибьюторов.
