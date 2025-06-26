# 📖 AI ChatBot - Developer Guide
This guide contains all the necessary information for local development, testing, and making changes to the project.

## 1. Setting Up the Local Environment
### 1.1. Prerequisites
- Docker and Docker Compose (recommended for the full stack)
- Node.js (v18+) and npm
- Python (v3.9+) and pip
- virtualenv for dependency isolation

### 1.2. Backend
```bash
cd backend
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # for Linux/macOS
# venv\Scripts\activate  # for Windows
# Install dependencies
pip install -r requirements.txt
# For development:
pip install -r requirements-dev.txt
# Copy .env and fill in the keys
cp ../config/.env.template ../.env
nano ../.env
```

### 1.3. Frontend
```bash
cd frontend
# Install dependencies
npm install
```

## 2. Running in Development Mode
### 2.1. Using Docker (Recommended)
Docker Compose is set up for hot-reload. Changes in backend and frontend code are automatically applied inside containers without needing to restart them.
```bash
# Start all services (backend, frontend, redis, chromadb, celery)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### 2.2. Locally (without Docker)
This method is useful for detailed debugging of a specific service. Start each service in a separate terminal.
```bash
# Terminal 1: Redis
redis-server
# Terminal 2: ChromaDB (optional, if using RAG)
# see instructions in docs/ARCHITECTURE.md
# Terminal 3: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Terminal 4: Celery worker (if used)
celery -A app.worker.celery_app worker --loglevel=info
# Terminal 5: Frontend
cd frontend
npm start
```

## 3. Testing
### 3.1. Backend Tests
We use pytest for unit and integration tests.
```bash
cd backend
source venv/bin/activate
# Run all tests in verbose mode
pytest -v
# Run tests with code coverage report
pytest --cov=app
```

## 4. Code Style and Quality
To maintain a unified code style and prevent simple errors, please use linters before committing.

### 4.1. Backend (Python)
- Formatting: black
- Linting: flake8
```bash
cd backend
black . && flake8 .
```

### 4.2. Frontend (TypeScript/React)
- Formatting: prettier
- Linting: eslint
```bash
cd frontend
npm run format && npm run lint
```

## 5. Architecture Features and Dependency Injection
- All services use DI (dependency injection) via FastAPI.
- AIService uses lazy initialization of providers.
- VectorMemoryService is implemented as a Singleton.
- VoiceService processing status is stored in Redis.
- Nginx is an optional component, used only in production.

## 6. 🔥 How to Add a New AI Provider
- Create a provider file: In `backend/app/services/ai_providers/`, create `my_provider.py`.
- Implement a class inheriting from BaseAIProvider and implement all its abstract methods (`generate_response`, `generate_streaming_response`, etc.).
```python
from .base import BaseAIProvider
class MyProvider(BaseAIProvider):
    async def generate_response(self, ...):
        # Your logic for the new provider's API request
        pass
    # ... other methods
```
- Register the provider: In `backend/app/services/ai_service.py`, import your new class and add it to the initialization logic in the `_initialize_providers` method.
```python
# In the _initialize_providers() method of AIService
if self.settings.my_provider_api_key:
    self.providers["my_provider_name"] = MyProvider(...)
```
- Add configuration: Add the necessary variables (e.g., `MY_PROVIDER_API_KEY`) to `backend/app/core/config.py` and to the template file `config/.env.template`.

Done! After restarting, your provider will be automatically discovered and available for selection in the system. 