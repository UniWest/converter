# Интеграция Celery для асинхронной обработки задач

Этот документ описывает интеграцию Celery в Django проект для асинхронной обработки задач конвертации файлов.

## Компоненты системы

### 1. Основные компоненты

- **Celery Worker** - воркер для выполнения задач конвертации
- **Redis** - брокер сообщений и backend для результатов
- **Celery Beat** - планировщик периодических задач
- **Flower** - веб-интерфейс для мониторинга

### 2. Архитектура очередей

Система использует разделение по очередям для оптимальной обработки:

- `video` - конвертация видео (ресурсоёмкие задачи)
- `audio` - конвертация аудио
- `image` - обработка изображений
- `document` - конвертация документов
- `archive` - работа с архивами
- `cleanup` - очистка временных файлов

## Установка и настройка

### 1. Установка Redis

**Windows:**
```bash
# Скачайте и установите Redis для Windows
# Или используйте Docker:
docker run -d -p 6379:6379 redis:alpine
```

**Linux/macOS:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server

# macOS
brew install redis
```

### 2. Установка Python зависимостей

```bash
# Активируйте виртуальное окружение
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Установите зависимости
pip install -r requirements.txt
```

### 3. Применение миграций Django

```bash
python manage.py makemigrations
python manage.py migrate

# Миграции для django-celery-beat
python manage.py migrate django_celery_beat
```

## Запуск системы

### 1. Автоматический запуск (Windows)

```bash
# Запуск всех компонентов одной командой
start_celery_workers.bat
```

Этот скрипт запустит:
- Основной Celery worker
- Worker для очистки файлов
- Celery Beat (планировщик)
- Flower (мониторинг)

### 2. Ручной запуск

**Запуск Redis:**
```bash
redis-server
```

**Запуск основного воркера:**
```bash
celery -A converter_site worker --loglevel=info --concurrency=2 --queues=video,audio,image,document,archive,default
```

**Запуск воркера для очистки:**
```bash
celery -A converter_site worker --loglevel=info --concurrency=1 --queues=cleanup
```

**Запуск планировщика:**
```bash
celery -A converter_site beat --loglevel=info
```

**Запуск мониторинга:**
```bash
celery -A converter_site flower --port=5555
```

## Использование в коде

### 1. Создание задачи конвертации

```python
from converter.tasks import convert_video
from converter.models import ConversionTask

# Создание записи задачи в БД
task = ConversionTask.objects.create()
task.set_metadata(
    input_file="/path/to/input.mp4",
    output_format="webm",
    quality="high"
)
task.save()

# Запуск асинхронной задачи
result = convert_video.delay(
    task_id=str(task.id),
    input_path="/path/to/input.mp4",
    output_format="webm",
    quality="high"
)

print(f"Задача отправлена: {result.task_id}")
```

### 2. Отслеживание прогресса

```python
from converter.models import ConversionTask

task = ConversionTask.objects.get(id=task_id)

print(f"Статус: {task.status}")
print(f"Прогресс: {task.progress}%")

if task.is_finished:
    if task.status == ConversionTask.STATUS_DONE:
        output_file = task.get_metadata('output_file')
        print(f"Готово! Файл: {output_file}")
    else:
        print(f"Ошибка: {task.error_message}")
```

### 3. Отмена задачи

```python
from celery_app import app

# Отмена задачи через Celery
app.control.revoke(task_id, terminate=True)

# Обновление статуса в БД
task = ConversionTask.objects.get(id=task_id)
task.fail("Задача отменена пользователем")
```

## Конфигурация

### 1. Настройки в settings.py

Основные параметры конфигурации:

```python
# Таймауты
CELERY_TASK_SOFT_TIME_LIMIT = 600  # 10 минут
CELERY_TASK_TIME_LIMIT = 900       # 15 минут

# Повторные попытки
CELERY_TASK_RETRY_DELAY = 60       # 1 минута
CELERY_TASK_MAX_RETRIES = 3        # Максимум 3 попытки

# Воркеры
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
```

### 2. Периодические задачи

Система автоматически выполняет:

- **Очистка временных файлов** - каждые 6 часов
- **Очистка старых записей задач** - ежедневно в 3:00

## Мониторинг и отладка

### 1. Flower Dashboard

Откройте в браузере: http://localhost:5555

Возможности:
- Просмотр активных задач
- Мониторинг воркеров
- Статистика производительности
- Логи выполнения

### 2. Логирование

Логи сохраняются в стандартный вывод и могут быть перенаправлены в файлы:

```bash
# Сохранение логов в файл
celery -A converter_site worker --loglevel=info > celery_worker.log 2>&1
```

### 3. Проверка статуса системы

```python
# Проверка доступности Redis
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
print(r.ping())  # True если Redis доступен

# Проверка активных воркеров
from celery_app import app
inspect = app.control.inspect()
print(inspect.active())  # Активные задачи
print(inspect.stats())   # Статистика воркеров
```

## Обработка ошибок

### 1. Типы ошибок

- **SoftTimeLimitExceeded** - превышен мягкий лимит времени
- **TimeLimitExceeded** - превышен жёсткий лимит времени
- **WorkerLostError** - воркер завершился неожиданно
- **Retry** - задача будет повторена

### 2. Стратегии восстановления

1. **Автоматические повторы** - до 3 попыток с задержкой в 1 минуту
2. **Очистка ресурсов** - автоматическое удаление временных файлов
3. **Уведомления об ошибках** - запись в логи и базу данных

## Оптимизация производительности

### 1. Настройка воркеров

```bash
# Для видео (ресурсоёмко)
celery -A converter_site worker --queues=video --concurrency=1

# Для лёгких задач
celery -A converter_site worker --queues=image,document --concurrency=4
```

### 2. Управление памятью

- `CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000` - перезапуск воркера после 1000 задач
- Мониторинг использования памяти через Flower
- Автоматическая очистка временных файлов

### 3. Приоритизация задач

```python
# Высокий приоритет
convert_video.apply_async(args=[...], priority=9)

# Обычный приоритет
convert_video.delay(...)
```

## Безопасность

### 1. Аутентификация Redis

```python
CELERY_BROKER_URL = 'redis://:password@localhost:6379/0'
```

### 2. Ограничения доступа

- Flower доступен только локально (127.0.0.1:5555)
- Redis binding только на локальный интерфейс
- Валидация входных данных в задачах

## Масштабирование

### 1. Горизонтальное масштабирование

```bash
# Запуск дополнительных воркеров на других машинах
celery -A converter_site worker --hostname=worker2@%h
celery -A converter_site worker --hostname=worker3@%h
```

### 2. Мониторинг нагрузки

- Отслеживание длины очередей в Flower
- Мониторинг времени выполнения задач
- Автоматическое масштабирование по нагрузке

## Часто задаваемые вопросы

### Q: Что делать если задача зависла?

```python
# Принудительная отмена задачи
from celery_app import app
app.control.revoke('task-id', terminate=True, signal='KILL')
```

### Q: Как очистить очереди?

```bash
# Очистка всех очередей
celery -A converter_site purge

# Очистка конкретной очереди
celery -A converter_site purge --queues=video
```

### Q: Как перезапустить воркеры?

```bash
# Мягкий перезапуск
celery -A converter_site control pool_restart

# Перезапуск с завершением текущих задач
pkill -f "celery worker"
# Затем запустите воркеры заново
```

## Заключение

Интеграция Celery обеспечивает:

- ✅ Асинхронную обработку файлов
- ✅ Надёжность с автоматическими повторами
- ✅ Масштабируемость с несколькими воркерами
- ✅ Мониторинг через Flower
- ✅ Автоматическую очистку ресурсов
- ✅ Обработку различных типов файлов в специализированных очередях

Система готова к использованию в продакшене и может обрабатывать большие объёмы файлов с высокой надёжностью.
