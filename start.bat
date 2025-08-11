@echo off
chcp 65001 >nul

echo 🚀 Запуск конвертера медиафайлов...

REM Проверка виртуального окружения
if "%VIRTUAL_ENV%"=="" (
    echo ⚠️  Виртуальное окружение не активировано!
    echo Запустите: .venv\Scripts\activate
    pause
    exit /b 1
)

REM Проверка зависимостей
echo 📦 Проверка зависимостей...
pip install -q -r requirements.txt

REM Проверка Redis
echo 🔍 Проверка Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo ❌ Redis не запущен! Запустите Redis сервер.
    echo Windows: Запустите redis-server.exe или установите через Docker
    echo Docker: docker run -d -p 6379:6379 redis:alpine
    pause
    exit /b 1
)
echo ✅ Redis работает

REM Применение миграций
echo 🗄️  Применение миграций...
python manage.py migrate

REM Сбор статических файлов
echo 📁 Сбор статических файлов...
python manage.py collectstatic --noinput

REM Создание директорий
echo 📂 Создание необходимых директорий...
if not exist "media" mkdir media
if not exist "temp" mkdir temp
if not exist "staticfiles" mkdir staticfiles

REM Проверка FFmpeg
echo 🎬 Проверка FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FFmpeg не найден. Установите для лучшей производительности.
) else (
    echo ✅ FFmpeg найден
)

echo.
echo 🎉 Запуск сервисов...
echo 📱 Веб-приложение: http://localhost:8000
echo 🌸 Мониторинг Celery: http://localhost:5555
echo.
echo Для остановки закройте все окна или нажмите Ctrl+C

REM Запуск Django сервера в новом окне
start "Django Server" cmd /k "python manage.py runserver 0.0.0.0:8000"

REM Ждем немного для запуска Django
timeout /t 3 /nobreak >nul

REM Запуск Celery Worker в новом окне
start "Celery Worker" cmd /k "celery -A converter_site worker --loglevel=info --concurrency=2"

REM Запуск Celery Beat в новом окне
start "Celery Beat" cmd /k "celery -A converter_site beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler"

REM Запуск Flower в новом окне (если доступен)
flower --version >nul 2>&1
if not errorlevel 1 (
    start "Flower Monitor" cmd /k "celery -A converter_site flower --port=5555"
)

echo Все сервисы запущены в отдельных окнах!
pause
