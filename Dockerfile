# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    # FFmpeg для обработки аудио/видео
    ffmpeg \
    # Библиотеки для обработки изображений
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    # Библиотеки для аудио обработки
    libsndfile1 \
    libsox-fmt-all \
    sox \
    # Системные утилиты
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    # Очистка кэша
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .
COPY .env.example .env

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Создаем директории для медиа файлов
RUN mkdir -p /app/media /app/temp /app/staticfiles

# Копируем исходный код приложения
COPY . .

# Устанавливаем права на выполнение скриптов
RUN chmod +x manage.py

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app_user && \
    chown -R app_user:app_user /app
USER app_user

# Экспонируем порт
EXPOSE 8000

# Команда по умолчанию
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
