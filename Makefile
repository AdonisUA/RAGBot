.PHONY: install env start-backend start-frontend start test clean

install:
	pip install -r backend/requirements.txt

install-dev:
	pip install -r backend/requirements-dev.txt
	cd frontend && npm install

env:
	cp -n config/.env.template .env || true

start-backend:
	cd backend && uvicorn app.main:app --reload

start-frontend:
	cd frontend && npm start

start: install env
	$(MAKE) -j2 start-backend start-frontend

test:
	pytest

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf .pytest_cache
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.log' -delete 