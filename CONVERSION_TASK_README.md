# Модель ConversionTask - Документация

## Описание

Модель `ConversionTask` предназначена для отслеживания статуса и прогресса задач конвертации файлов. Она предоставляет удобный API для управления жизненным циклом задач конвертации.

## Поля модели

### Основные поля:
- **status** - Статус задачи (queued, running, done, failed)
- **progress** - Прогресс выполнения от 0 до 100%
- **task_metadata** - JSON с метаданными задачи

### Временные метки:
- **created_at** - Время создания задачи
- **updated_at** - Время последнего обновления
- **started_at** - Время начала выполнения
- **completed_at** - Время завершения

### Дополнительные поля:
- **error_message** - Сообщение об ошибке (для неудачных задач)

## Статусы задач

1. **queued** - В очереди (задача создана, но не начата)
2. **running** - Выполняется (задача в процессе обработки)
3. **done** - Завершено (задача успешно выполнена)
4. **failed** - Ошибка (задача завершилась с ошибкой)

## Пример метаданных

```json
{
  "original_filename": "video.mp4",
  "input_format": "mp4",
  "output_format": "avi",
  "file_size_mb": 125.7,
  "user_ip": "192.168.1.100",
  "conversion_settings": {
    "quality": "high",
    "resolution": "1920x1080",
    "codec": "h264"
  },
  "upload_path": "/tmp/uploads/video.mp4",
  "output_path": "/tmp/converted/video.avi"
}
```

## API модели

### Создание задачи
```python
from converter.models import ConversionTask

# Создание новой задачи
task = ConversionTask.objects.create(
    task_metadata={
        'original_filename': 'video.mp4',
        'input_format': 'mp4',
        'output_format': 'avi',
        'file_size_mb': 125.7
    }
)
```

### Управление жизненным циклом
```python
# Запуск задачи
task.start()

# Обновление прогресса
task.update_progress(50)

# Успешное завершение
task.complete()

# Завершение с ошибкой
task.fail("Описание ошибки")
```

### Работа с метаданными
```python
# Установка метаданных
task.set_metadata(
    user_id=123,
    conversion_quality='high'
)

# Получение метаданных
filename = task.get_metadata('original_filename', 'unknown.file')
```

### Свойства модели
```python
# Проверка состояния
if task.is_finished:
    print("Задача завершена")

if task.is_active:
    print("Задача активна")

# Получение длительности
duration = task.duration
```

## Интеграция с админкой Django

Модель автоматически регистрируется в админке Django с:
- Цветовой индикацией статусов
- Прогресс-барами
- Удобным отображением метаданных
- Возможностью перезапуска неудачных задач

## Использование в представлениях (Views)

### Создание задачи при загрузке файла
```python
from django.http import JsonResponse
from converter.models import ConversionTask

def convert_file(request):
    if request.method == 'POST':
        # Создаем задачу
        task = ConversionTask.objects.create(
            task_metadata={
                'original_filename': request.FILES['file'].name,
                'input_format': 'mp4',
                'output_format': request.POST.get('output_format'),
                'user_ip': request.META.get('REMOTE_ADDR')
            }
        )
        
        # Запускаем обработку (асинхронно)
        process_conversion_task.delay(task.id)
        
        return JsonResponse({
            'task_id': task.id,
            'status': task.status
        })
```

### Получение статуса задачи
```python
def task_status(request, task_id):
    try:
        task = ConversionTask.objects.get(id=task_id)
        return JsonResponse({
            'id': task.id,
            'status': task.status,
            'progress': task.progress,
            'error': task.error_message,
            'is_finished': task.is_finished
        })
    except ConversionTask.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
```

## Интеграция с Celery

### Задача Celery для обработки конвертации
```python
from celery import shared_task
from converter.models import ConversionTask
import subprocess
import os

@shared_task
def process_conversion_task(task_id):
    try:
        task = ConversionTask.objects.get(id=task_id)
        task.start()
        
        # Получаем параметры из метаданных
        input_file = task.get_metadata('upload_path')
        output_file = task.get_metadata('output_path')
        
        # Процесс конвертации с обновлением прогресса
        # ... код конвертации с FFmpeg ...
        
        # Имитация прогресса
        for progress in range(10, 101, 10):
            task.update_progress(progress)
            time.sleep(1)  # Реальная работа здесь
        
        task.complete()
        
    except Exception as e:
        task.fail(str(e))
        raise
```

## Запросы и фильтрация

### Полезные запросы
```python
# Все активные задачи
active_tasks = ConversionTask.objects.filter(
    status__in=[ConversionTask.STATUS_QUEUED, ConversionTask.STATUS_RUNNING]
)

# Задачи за последний час
from django.utils import timezone
recent_tasks = ConversionTask.objects.filter(
    created_at__gte=timezone.now() - timezone.timedelta(hours=1)
)

# Неудачные задачи
failed_tasks = ConversionTask.objects.filter(
    status=ConversionTask.STATUS_FAILED
)

# Статистика по статусам
from django.db.models import Count
stats = ConversionTask.objects.values('status').annotate(
    count=Count('id')
)
```

## Лучшие практики

### 1. Всегда используйте try-catch при работе с задачами
```python
try:
    task = ConversionTask.objects.get(id=task_id)
    # работа с задачей
except ConversionTask.DoesNotExist:
    # обработка отсутствующей задачи
```

### 2. Сохраняйте важную информацию в метаданных
```python
task.set_metadata(
    original_filename=file.name,
    file_size=file.size,
    user_id=request.user.id,
    conversion_settings=form.cleaned_data
)
```

### 3. Обновляйте прогресс регулярно
```python
# В длительных операциях
for i, step in enumerate(processing_steps):
    # выполнение шага
    progress = int((i + 1) / len(processing_steps) * 100)
    task.update_progress(progress)
```

### 4. Правильно обрабатывайте ошибки
```python
try:
    # код конвертации
    task.complete()
except Exception as e:
    task.fail(f"Ошибка конвертации: {str(e)}")
    raise
```

## Индексы и производительность

Модель создает индексы для часто используемых полей:
- `status` - для быстрого поиска задач по статусу
- `created_at` - для сортировки по времени создания
- `-created_at` - для сортировки в обратном порядке

## Миграции

Модель создает следующую миграцию:
- Создание таблицы `converter_conversiontask`
- Создание индексов для оптимизации запросов
- Настройка ограничений для поля `progress` (0-100)

## Расширение модели

Для добавления новых полей создавайте миграции:

```python
# Новые поля
priority = models.IntegerField(default=0)
estimated_duration = models.DurationField(null=True, blank=True)

# Создание миграции
python manage.py makemigrations converter
python manage.py migrate
```

## Мониторинг и аналитика

### Создание отчетов
```python
from django.db.models import Avg, Count
from django.utils import timezone

# Средняя длительность выполнения
avg_duration = ConversionTask.objects.filter(
    status=ConversionTask.STATUS_DONE,
    duration__isnull=False
).aggregate(Avg('duration'))

# Количество задач по дням
daily_stats = ConversionTask.objects.filter(
    created_at__date=timezone.now().date()
).values('status').annotate(count=Count('id'))
```

## Очистка старых задач

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Удаляем задачи старше 30 дней
        cutoff_date = timezone.now() - timedelta(days=30)
        old_tasks = ConversionTask.objects.filter(
            created_at__lt=cutoff_date,
            status__in=[ConversionTask.STATUS_DONE, ConversionTask.STATUS_FAILED]
        )
        count = old_tasks.count()
        old_tasks.delete()
        print(f"Удалено {count} старых задач")
```
