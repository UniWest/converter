#!/bin/bash

# Скрипт быстрого запуска для разработки

echo "🚀 Запуск конвертера медиафайлов..."

# Проверка виртуального окружения
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Виртуальное окружение не активировано!"
    echo "Запустите: source .venv/bin/activate"
    exit 1
fi

# Проверка зависимостей
echo "📦 Проверка зависимостей..."
pip install -q -r requirements.txt

# Проверка Redis
echo "🔍 Проверка Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis не запущен! Запустите Redis сервер."
    echo "Ubuntu/Debian: sudo systemctl start redis"
    echo "macOS: brew services start redis"
    echo "Docker: docker run -d -p 6379:6379 redis:alpine"
    exit 1
fi
echo "✅ Redis работает"

# Применение миграций
echo "🗄️  Применение миграций..."
python manage.py migrate

# Сбор статических файлов
echo "📁 Сбор статических файлов..."
python manage.py collectstatic --noinput

# Создание директорий
echo "📂 Создание необходимых директорий..."
mkdir -p media temp staticfiles

# Проверка FFmpeg
echo "🎬 Проверка FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg найден: $(ffmpeg -version | head -1)"
else
    echo "⚠️  FFmpeg не найден. Установите для лучшей производительности."
fi

# Запуск в фоне
echo "🏃 Запуск сервисов..."

# Django сервер
python manage.py runserver 0.0.0.0:8000 &
DJANGO_PID=$!

# Celery Worker
celery -A converter_site worker --loglevel=info --concurrency=2 &
CELERY_WORKER_PID=$!

# Celery Beat
celery -A converter_site beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler &
CELERY_BEAT_PID=$!

# Flower (опционально)
if command -v flower &> /dev/null; then
    celery -A converter_site flower --port=5555 &
    FLOWER_PID=$!
    echo "🌸 Flower мониторинг: http://localhost:5555"
fi

echo ""
echo "🎉 Все сервисы запущены!"
echo "📱 Веб-приложение: http://localhost:8000"
echo "🌸 Мониторинг Celery: http://localhost:5555"
echo ""
echo "Для остановки нажмите Ctrl+C"

# Обработчик сигнала для остановки всех процессов
cleanup() {
    echo ""
    echo "🛑 Остановка сервисов..."
    kill $DJANGO_PID $CELERY_WORKER_PID $CELERY_BEAT_PID 2>/dev/null
    if [[ ! -z "$FLOWER_PID" ]]; then
        kill $FLOWER_PID 2>/dev/null
    fi
    echo "✅ Все сервисы остановлены"
    exit 0
}

trap cleanup INT TERM

# Ожидание
wait
