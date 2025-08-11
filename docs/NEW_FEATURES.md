# Новые функции системы конвертации

Документация по новым функциям, добавленным в Step 7.

## 1. Команда управления `cleanup_old_files`

### Описание

Команда Django для очистки старых файлов и задач конвертации. Помогает поддерживать чистоту базы данных и файловой системы.

### Расположение

```
converter/management/commands/cleanup_old_files.py
```

### Использование

#### Базовое использование
```bash
# Очистить задачи старше 7 дней (по умолчанию)
python manage.py cleanup_old_files

# Очистить задачи старше 30 дней
python manage.py cleanup_old_files --days=30
```

#### Расширенные опции
```bash
# Режим тестирования (ничего не удаляет)
python manage.py cleanup_old_files --dry-run

# Очистить только неудачные задачи
python manage.py cleanup_old_files --failed-only

# Очистить только завершенные задачи
python manage.py cleanup_old_files --completed-only

# Включить очистку файлов
python manage.py cleanup_old_files --cleanup-files

# Подробный вывод
python manage.py cleanup_old_files --verbosity=2
```

#### Комбинированное использование
```bash
# Очистить неудачные задачи старше 3 дней с удалением файлов
python manage.py cleanup_old_files --days=3 --failed-only --cleanup-files --verbosity=2

# Тестовый прогон с подробным выводом
python manage.py cleanup_old_files --days=14 --dry-run --verbosity=2
```

### Параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--days` | Количество дней для сохранения | 7 |
| `--dry-run` | Режим тестирования (не удаляет) | False |
| `--failed-only` | Удалять только неудачные задачи | False |
| `--completed-only` | Удалять только завершенные задачи | False |
| `--cleanup-files` | Удалять связанные файлы | False |

### Логирование

Команда ведет подробное логирование:
- Количество найденных задач
- Количество удаленных задач
- Размер очищенного пространства (при --cleanup-files)
- Ошибки при удалении

### Автоматизация

Рекомендуется добавить в cron для регулярной очистки:

```bash
# Каждый день в 2:00 очищать задачи старше 30 дней
0 2 * * * cd /path/to/project && python manage.py cleanup_old_files --days=30 --cleanup-files

# Каждую неделю очищать неудачные задачи старше 7 дней
0 3 * * 0 cd /path/to/project && python manage.py cleanup_old_files --days=7 --failed-only --cleanup-files
```

## 2. Расширенный endpoint `/status`

### Описание

Расширенная версия endpoint'а для проверки состояния системы конвертации. Предоставляет детальную информацию о системе, ресурсах, инструментах и задачах.

### URL

```
GET /status/
```

### Ответ

Возвращает JSON с подробной информацией о системе:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "status": "healthy",
  "system": {
    "platform": "Windows-10-10.0.19041-SP0",
    "python_version": "3.11.0",
    "architecture": "64bit"
  },
  "resources": {
    "cpu_count": 8,
    "memory_total": 17179869184,
    "memory_available": 8589934592,
    "disk_usage": {
      "total": 1000204886016,
      "free": 500102443008,
      "used": 500102443008
    }
  },
  "engines": {
    "moviepy": {
      "available": true,
      "version": "1.0.3",
      "path": "/path/to/moviepy/__init__.py",
      "status": "available"
    },
    "ffmpeg": {
      "available": true,
      "version": "4.4.2",
      "path": "ffmpeg",
      "executable": true,
      "status": "available"
    }
  },
  "binaries": {
    "ffprobe": {
      "available": true,
      "version": "ffprobe version 4.4.2",
      "path": "ffprobe",
      "status": "available"
    },
    "imagemagick": {
      "available": false,
      "version": null,
      "path": "convert",
      "status": "binary_not_found"
    },
    "gifsicle": {
      "available": true,
      "version": "Gifsicle 1.93",
      "path": "gifsicle",
      "status": "available"
    }
  },
  "media_paths": {
    "media_root": "/path/to/media",
    "media_root_exists": true,
    "gifs_dir": "/path/to/media/gifs",
    "gifs_dir_exists": true,
    "uploads_dir": "/path/to/media/uploads",
    "uploads_dir_exists": true,
    "temp_dir": "/path/to/temp",
    "temp_dir_exists": false
  },
  "statistics": {
    "total_tasks": 150,
    "queued_tasks": 5,
    "running_tasks": 2,
    "completed_tasks": 140,
    "failed_tasks": 3
  },
  "storage": {
    "gifs_size": 524288000,
    "uploads_size": 1048576000,
    "temp_size": 0
  },
  "recommended_engine": "MoviePy (с поддержкой FFmpeg)"
}
```

### Секции ответа

#### `system`
Информация о системе:
- `platform` - операционная система
- `python_version` - версия Python
- `architecture` - архитектура процессора

#### `resources`
Ресурсы системы:
- `cpu_count` - количество CPU ядер
- `memory_total` - общий объем памяти (байты)
- `memory_available` - доступная память (байты)
- `disk_usage` - использование диска

#### `engines`
Движки конвертации:
- `moviepy` - статус MoviePy
- `ffmpeg` - статус FFmpeg

#### `binaries`
Дополнительные инструменты:
- `ffprobe` - для анализа видео
- `imagemagick` - для обработки изображений
- `gifsicle` - для оптимизации GIF

#### `media_paths`
Пути к медиа файлам:
- Проверка существования директорий
- Пути к основным папкам

#### `statistics`
Статистика задач:
- Общее количество задач
- Распределение по статусам

#### `storage`
Использование хранилища:
- Размеры папок в байтах

### Статусы системы

- `healthy` - система работает нормально
- `critical` - критические проблемы (нет движков конвертации)
- `error` - произошла ошибка при получении статуса

### Использование в коде

#### Python
```python
import requests

response = requests.get('http://localhost:8000/status/')
status_data = response.json()

if status_data['status'] == 'healthy':
    print("Система работает нормально")
    
# Проверка доступности FFmpeg
ffmpeg_available = status_data['engines']['ffmpeg']['available']
```

#### JavaScript
```javascript
fetch('/status/')
  .then(response => response.json())
  .then(data => {
    console.log('Система:', data.status);
    console.log('Всего задач:', data.statistics.total_tasks);
    console.log('Рекомендуемый движок:', data.recommended_engine);
  });
```

#### cURL
```bash
curl -X GET http://localhost:8000/status/ | jq .
```

### Мониторинг

Endpoint можно использовать для мониторинга:

```bash
#!/bin/bash
# Скрипт мониторинга
STATUS=$(curl -s http://localhost:8000/status/ | jq -r '.status')

if [ "$STATUS" != "healthy" ]; then
    echo "ALERT: Система конвертации в состоянии: $STATUS"
    # Отправка уведомления
fi
```

## 3. Зависимости

### Новые пакеты

Добавлен пакет `psutil` для мониторинга ресурсов системы:

```txt
psutil>=5.9.0
```

### Установка

```bash
pip install psutil>=5.9.0

# Или через requirements.txt
pip install -r requirements.txt
```

## 4. Тестирование

### Запуск тестов

```bash
# Запуск тестового скрипта
python test_new_features.py

# Тестирование только команды очистки
python manage.py cleanup_old_files --dry-run --verbosity=2

# Тестирование endpoint статуса
curl -X GET http://localhost:8000/status/ | jq .
```

### Создание тестовых данных

```python
from converter.models import ConversionTask
from datetime import datetime, timedelta

# Создание старой задачи для тестирования очистки
ConversionTask.objects.create(
    status=ConversionTask.STATUS_DONE,
    progress=100,
    created_at=datetime.now() - timedelta(days=30),
    task_metadata={'filename': 'test_video.mp4'}
)
```

## 5. Производительность

### Команда очистки
- Использует эффективные Django ORM запросы
- Поддерживает батчевое удаление
- Минимальная нагрузка на базу данных

### Endpoint статуса
- Кэширует результаты системных вызовов
- Быстрые запросы к базе данных
- Таймауты для внешних команд (5-10 секунд)

## 6. Безопасность

### Команда очистки
- Проверка прав доступа к файлам
- Валидация путей
- Логирование всех операций

### Endpoint статуса
- Не раскрывает чувствительную информацию
- Обработка ошибок без детализации
- Ограничение информации о системе

## 7. Рекомендации

### Регулярная очистка
1. Настройте cron для ежедневной очистки
2. Используйте разные интервалы для разных типов задач
3. Регулярно проверяйте логи очистки

### Мониторинг
1. Интегрируйте `/status` в системы мониторинга
2. Настройте алерты на критические состояния
3. Отслеживайте тренды использования ресурсов

### Производительность
1. Очищайте неудачные задачи чаще
2. Мониторьте размер медиа папок
3. Настройте ротацию логов
