#!/bin/bash

# Скрипт для остановки всех процессов Celery

echo "Остановка всех процессов Celery..."

# Останавливаем все процессы Celery
pkill -f "celery worker"
pkill -f "celery beat" 
pkill -f "celery flower"

echo "Все процессы Celery остановлены."

# Опционально - очищаем PID файлы, если они существуют
if [ -d "pids" ]; then
    rm -f pids/*.pid
    echo "PID файлы очищены."
fi

echo "Готово!"
