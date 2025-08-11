# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies with FFmpeg
RUN apt-get update && apt-get install -y \
    # FFmpeg for audio/video processing - REQUIRED
    ffmpeg \
    # Verify FFmpeg installation
    && ffmpeg -version \
    # Image processing libraries
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    # Audio processing libraries
    libsndfile1 \
    libsox-fmt-all \
    sox \
    # System utilities
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    # Clean up cache
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

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

# Копируем скрипт запуска для Docker-платформ (Railway) с правами исполнения (Dockerfile v1.2)
COPY --chmod=0755 scripts/start.sh /app/scripts/start.sh

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app_user && \
    chown -R app_user:app_user /app
USER app_user

# Экспонируем порт
EXPOSE 8000

# Команда по умолчанию (Railway будет передавать $PORT)
CMD ["/bin/bash", "-lc", "/app/scripts/start.sh"]
