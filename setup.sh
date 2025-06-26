#!/bin/bash
set -e

check_tools() {
    echo "Проверка необходимых инструментов..."
    if ! command -v pip &> /dev/null; then
        echo "Ошибка: pip не установлен. Пожалуйста, установите pip."
        exit 1
    fi
    if ! command -v npm &> /dev/null; then
        echo "Ошибка: npm не установлен. Пожалуйста, установите npm."
        exit 1
    fi
    echo "Все необходимые инструменты установлены."
}

check_tools

# Установка зависимостей
echo "[1/5] Установка зависимостей backend..."
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

echo "[2/5] Установка зависимостей frontend..."
cd frontend && npm install && cd ..

# Генерация .env, если не существует
if [ ! -f .env ]; then
  echo "[3/5] Копирую .env.template -> .env"
  cp config/.env.template .env
  echo "[3/5] Пожалуйста, отредактируйте файл .env и добавьте ваш API-ключ AI-провайдера!"
  echo ""
  echo "Требуется: хотя бы один из OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY"
  echo ""
  read -p "Нажмите Enter, чтобы продолжить после редактирования файла .env..."
fi

# Запуск сервисов с Docker Compose
echo "[4/5] Запуск сервисов с Docker Compose..."
docker compose up --build -d

echo "Все сервисы запущены!" 