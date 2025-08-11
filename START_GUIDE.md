# Руководство по запуску проекта с Celery

## Текущий статус

✅ **Celery успешно интегрирован в проект**

Система готова к запуску и тестированию. Все зависимости установлены, миграции выполнены.

## Новые возможности

### 1. Аудио в текст (Speech-to-Text)
- Форма: `AudioToTextForm` в `forms.py`
- Celery задача: `convert_audio_to_text` в `converter_site/tasks.py`
- Поддержка: MP3, WAV, M4A, FLAC, OGG, AAC, WMA
- Языки: русский, английский, испанский, французский и другие
- Выводы: TXT, SRT, JSON

### 2. GIF из изображений
- Форма: `ImagesToGifForm` в `forms.py` с кастомным виджетом для множественных файлов
- Celery задача: `create_gif_from_images` в `converter_site/tasks.py`
- Поддержка: JPG, PNG, WebP, BMP (до 100 изображений)
- Настройки: длительность кадров, размер, цвета, эффекты

### 3. Автоматическая очистка
- Задача: `cleanup_old_files` - удаление старых временных файлов
- Запуск: ежедневно в 3:00 (настроено в Celery Beat)

## Запуск проекта

### Шаг 1: Запуск Redis (обязательно!)

Celery требует Redis для работы. Запустите Redis перед запуском остальных компонентов.

**Windows:**
```cmd
# Если Redis установлен локально
redis-server

# Или через WSL
wsl
redis-server

# Или через Docker
docker run -d -p 6379:6379 --name redis redis:alpine
```

**Проверка Redis:**
```cmd
redis-cli ping
# Должен вернуть: PONG
```

### Шаг 2: Запуск Django сервера

```cmd
python manage.py runserver
```

Сервер запустится на http://127.0.0.1:8000/

### Шаг 3: Запуск Celery Worker (новое окно терминала)

```cmd
# Windows (используйте solo pool для разработки)
celery -A converter_site worker --loglevel=info --pool=solo

# Linux/macOS
celery -A converter_site worker --loglevel=info --concurrency=2
```

### Шаг 4: Запуск Celery Beat (новое окно терминала)

```cmd
celery -A converter_site beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Шаг 5: Запуск Flower (опционально, для мониторинга)

```cmd
celery -A converter_site flower
# Открыть http://localhost:5555
```

## Автоматический запуск

### Windows
```cmd
start_celery.bat
```

### Linux/macOS
```bash
chmod +x start_celery.sh
./start_celery.sh
```

## Тестирование новых функций

### Тест Celery соединения
```python
# В Django shell
python manage.py shell

>>> from converter_site.tasks import debug_task
>>> result = debug_task.delay()
>>> print(result.get())
# Должен вернуть: 'Debug task completed successfully'
```

### Тест аудио транскрипции
```python
>>> from converter_site.tasks import convert_audio_to_text
>>> options = {
...     'language': 'ru-RU',
...     'quality': 'standard',
...     'output_format': 'txt',
...     'enhance_speech': True
... }
>>> task = convert_audio_to_text.delay('/path/to/audio.mp3', options)
>>> print(f"Task ID: {task.id}")
>>> print(f"Status: {task.status}")
```

### Тест создания GIF
```python
>>> from converter_site.tasks import create_gif_from_images
>>> image_paths = ['/path/to/image1.jpg', '/path/to/image2.jpg']
>>> options = {
...     'frame_duration': 0.5,
...     'output_size': '480',
...     'colors': 128,
...     'loop': True
... }
>>> task = create_gif_from_images.delay(image_paths, options)
>>> print(f"Task ID: {task.id}")
```

## Структура проекта

```
converter_site/
├── __init__.py              # Импорт Celery (активирован)
├── celery_app.py            # Конфигурация Celery
├── tasks.py                 # Celery задачи (НОВОЕ)
└── settings.py              # Django настройки (обновлено)

forms.py                     # Новые формы (обновлено)
├── MultipleFileInput        # Кастомный виджет
├── AudioToTextForm          # Форма аудио → текст
└── ImagesToGifForm          # Форма изображения → GIF

requirements.txt             # Зависимости (обновлено)
start_celery.bat            # Windows скрипт (НОВОЕ)
start_celery.sh             # Linux/macOS скрипт (НОВОЕ)
CELERY_SETUP.md             # Документация
```

## Мониторинг

### Проверка статуса воркеров
```cmd
celery -A converter_site inspect active
celery -A converter_site inspect registered
celery -A converter_site inspect stats
```

### Flower веб-интерфейс
- URL: http://localhost:5555
- Мониторинг задач в реальном времени
- Управление воркерами
- Статистика выполнения

### Логи
- Celery Worker: в консоли или `logs/celery_worker.log`
- Celery Beat: в консоли или `logs/celery_beat.log`
- Django: стандартные логи Django

## Решение проблем

### Redis недоступен
```
[Errno 111] Connection refused
```
**Решение:** Запустите Redis сервер

### Задачи не выполняются
**Проверьте:**
1. Redis работает: `redis-cli ping`
2. Worker запущен: `celery -A converter_site inspect active`
3. Нет ошибок в логах воркера

### Импорт задач
```
KeyError: 'converter_site.tasks.convert_audio_to_text'
```
**Решение:** Перезапустите воркер после изменений в коде

### Зависимости для аудио обработки
Если возникают проблемы с аудио обработкой:
```cmd
# Windows может потребовать дополнительные библиотеки
pip install PyAudio
# Или используйте pre-compiled wheels
```

## Следующие шаги

1. **Создать веб-интерфейс** для новых форм в Django шаблонах
2. **Добавить AJAX** для отслеживания прогресса задач
3. **Настроить продакшен** с gunicorn, nginx, supervisor
4. **Добавить аутентификацию** для доступа к Flower
5. **Расширить тестирование** с unit тестами для задач

## Производительность

### Настройки для продакшена
```python
# settings.py для продакшена
CELERY_WORKER_CONCURRENCY = 4
CELERY_TASK_COMPRESSION = 'gzip'
CELERY_RESULT_COMPRESSION = 'gzip'
```

### Масштабирование
- Увеличьте количество воркеров при высокой нагрузке
- Используйте разные серверы для разных типов задач
- Настройте мониторинг ресурсов

---

## ✅ Готово к использованию!

Celery полностью интегрирован и готов к обработке:
- **Аудио транскрипции** с поддержкой множественных языков
- **Создания GIF анимаций** из наборов изображений
- **Автоматической очистки** временных файлов

Система настроена с таймаутами, повторными попытками, логированием и мониторингом.
