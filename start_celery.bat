@echo off
REM Скрипт для запуска Celery worker и beat на Windows
REM Используется для разработки и тестирования

echo Запуск Celery для проекта converter_site...

REM Создаем папку для логов если её нет
if not exist logs mkdir logs

REM Устанавливаем переменные окружения
set DJANGO_SETTINGS_MODULE=converter_site.settings
set CELERY_BROKER_URL=redis://localhost:6379/0
set CELERY_RESULT_BACKEND=redis://localhost:6379/0

echo Проверяем соединение с Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo Ошибка: Redis не доступен. Убедитесь, что Redis запущен.
    echo Вы можете запустить Redis с помощью: redis-server
    pause
    exit /b 1
)

echo Redis работает корректно.

REM Выполняем миграции
echo Выполняем миграции для Django...
python manage.py migrate

echo Создаем миграции для django-celery-beat...
python manage.py migrate django_celery_beat

echo.
echo Запуск Celery worker...
echo Откроется новое окно для worker. Не закрывайте его во время работы.

REM Запускаем Celery worker в новом окне
start "Celery Worker" cmd /k "celery -A converter_site worker --loglevel=info --concurrency=2 --pool=solo"

REM Ждем немного, чтобы worker успел запуститься
timeout /t 3 /nobreak >nul

echo.
echo Запуск Celery Beat...
echo Откроется ещё одно окно для beat scheduler.

REM Запускаем Celery beat в новом окне  
start "Celery Beat" cmd /k "celery -A converter_site beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler"

echo.
echo Celery запущен успешно!
echo.
echo Открытые окна:
echo   - Celery Worker (обработка задач)
echo   - Celery Beat (планировщик задач)
echo.
echo Для мониторинга можете запустить Flower:
echo   celery -A converter_site flower
echo   После запуска откройте http://localhost:5555
echo.
echo Для остановки закройте окна Celery Worker и Celery Beat
echo или используйте stop_celery.bat
echo.
pause
