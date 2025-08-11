#!/bin/bash

# Скрипт для запуска Celery worker и beat
# Используется для разработки и тестирования

echo "Запуск Celery для проекта converter_site..."

# Проверяем, что Redis запущен
echo "Проверяем соединение с Redis..."
redis-cli ping

if [ $? -ne 0 ]; then
    echo "Ошибка: Redis не доступен. Убедитесь, что Redis запущен."
    exit 1
fi

echo "Redis работает корректно."

# Устанавливаем переменные окружения
export DJANGO_SETTINGS_MODULE=converter_site.settings
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Запуск миграций для django-celery-beat (если не выполнены)
echo "Выполняем миграции для Django..."
python manage.py migrate

echo "Создаем периодические задачи..."
python manage.py migrate django_celery_beat

# Запуск Celery worker в фоне для разных очередей
echo "Запускаем Celery workers..."

# Worker для аудио обработки
celery -A converter_site worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=audio_processing \
    --hostname=audio_worker@%h \
    --logfile=logs/celery_audio.log \
    --detach

# Worker для обработки изображений  
celery -A converter_site worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=image_processing \
    --hostname=image_worker@%h \
    --logfile=logs/celery_image.log \
    --detach

# Worker для технических задач
celery -A converter_site worker \
    --loglevel=info \
    --concurrency=1 \
    --queues=maintenance \
    --hostname=maintenance_worker@%h \
    --logfile=logs/celery_maintenance.log \
    --detach

# Запуск Celery Beat (планировщик задач)
echo "Запускаем Celery Beat..."
celery -A converter_site beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --logfile=logs/celery_beat.log \
    --detach

echo "Celery запущен успешно!"
echo ""
echo "Логи:"
echo "  - Аудио worker: logs/celery_audio.log"
echo "  - Изображения worker: logs/celery_image.log" 
echo "  - Техническая обработка: logs/celery_maintenance.log"
echo "  - Beat scheduler: logs/celery_beat.log"
echo ""
echo "Для мониторинга запустите Flower:"
echo "  celery -A converter_site flower"
echo ""
echo "Для остановки всех процессов используйте:"
echo "  ./stop_celery.sh"
