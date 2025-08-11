@echo off
echo "Запуск Celery воркеров для конвертации файлов"
echo "============================================"

REM Активация виртуального окружения
echo Активация виртуального окружения...
call .venv\Scripts\activate.bat

REM Проверка Redis
echo Проверка подключения к Redis...
redis-cli ping
if %errorlevel% neq 0 (
    echo ОШИБКА: Redis недоступен. Убедитесь, что Redis запущен.
    pause
    exit /b 1
)

REM Запуск основного воркера для обработки различных типов файлов
echo Запуск основного Celery воркера...
start "Celery Main Worker" cmd /k "celery -A converter_site worker --loglevel=info --concurrency=2 --prefetch-multiplier=1 --queues=video,audio,image,document,archive,default"

REM Запуск воркера для очистки временных файлов
echo Запуск воркера для очистки...
start "Celery Cleanup Worker" cmd /k "celery -A converter_site worker --loglevel=info --concurrency=1 --queues=cleanup"

REM Запуск Celery Beat для периодических задач
echo Запуск Celery Beat (планировщик)...
start "Celery Beat" cmd /k "celery -A converter_site beat --loglevel=info"

REM Запуск Flower для мониторинга (опционально)
echo Запуск Flower для мониторинга...
start "Celery Flower" cmd /k "celery -A converter_site flower --port=5555"

echo.
echo Все воркеры запущены!
echo.
echo Доступные интерфейсы:
echo - Flower (мониторинг): http://localhost:5555
echo.
echo Для остановки всех воркеров просто закройте соответствующие окна.

pause
