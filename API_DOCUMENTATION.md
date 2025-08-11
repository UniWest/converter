# API Документация - Управление Задачами Конвертации

Данная документация описывает REST API для управления задачами конвертации файлов. API поддерживает создание задач через multipart/form-data и JSON с URL, проверку статуса, получение результатов и пакетное скачивание.

## Базовый URL

```
http://your-domain.com/api/tasks/
```

## Аутентификация

В текущей версии API не требует аутентификации. В продакшене рекомендуется добавить систему аутентификации (API ключи, JWT tokens, etc.).

## Формат ответов

Все ответы возвращаются в формате JSON. Успешные ответы содержат поле `"success": true`, а ошибки - `"success": false` с описанием ошибки в поле `"error"`.

---

## 1. Создание Задачи Конвертации

### POST `/api/tasks/create/`

Создает новую задачу конвертации. Поддерживает два формата запросов:

#### Вариант 1: Multipart Form-Data (загрузка файла)

```bash
curl -X POST http://your-domain.com/api/tasks/create/ \
  -F "file=@video.mp4" \
  -F "format=gif" \
  -F "width=480" \
  -F "fps=15" \
  -F "start_time=0" \
  -F "end_time=30" \
  -F "quality=medium" \
  -F "speed=1.0" \
  -F "grayscale=false" \
  -F "reverse=false" \
  -F "boomerang=false"
```

#### Вариант 2: JSON (URL файла)

```bash
curl -X POST http://your-domain.com/api/tasks/create/ \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://example.com/video.mp4",
    "format": "gif",
    "width": 480,
    "fps": 15,
    "start_time": 0,
    "end_time": 30,
    "quality": "medium",
    "speed": 1.0,
    "grayscale": false,
    "reverse": false,
    "boomerang": false
  }'
```

#### Параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `file` | File | Да (multipart) | Файл для конвертации |
| `url` | String | Да (JSON) | URL файла для скачивания и конвертации |
| `format` | String | Нет | Целевой формат (по умолчанию: "gif") |
| `width` | Integer | Нет | Ширина результата (сохраняет пропорции) |
| `fps` | Integer | Нет | Частота кадров (по умолчанию: 15) |
| `start_time` | Integer | Нет | Время начала в секундах (по умолчанию: 0) |
| `end_time` | Integer | Нет | Время окончания в секундах |
| `quality` | String | Нет | Качество: "low", "medium", "high" |
| `speed` | Float | Нет | Скорость воспроизведения (по умолчанию: 1.0) |
| `grayscale` | Boolean | Нет | Черно-белое изображение |
| `reverse` | Boolean | Нет | Обратное воспроизведение |
| `boomerang` | Boolean | Нет | Эффект бумеранга |
| `high_quality` | Boolean | Нет | Высокое качество |
| `dither` | String | Нет | Тип дизеринга (по умолчанию: "bayer") |
| `keep_original_size` | Boolean | Нет | Сохранить оригинальный размер |

#### Ответ

```json
{
  "success": true,
  "task_id": "123",
  "status": "queued",
  "message": "Задача создана и поставлена в очередь на выполнение",
  "api_urls": {
    "status": "/api/tasks/123/status/",
    "result": "/api/tasks/123/result/",
    "download": "/api/tasks/123/download/"
  }
}
```

---

## 2. Получение Статуса Задачи

### GET `/api/tasks/{task_id}/status/`

Возвращает текущий статус задачи конвертации.

```bash
curl http://your-domain.com/api/tasks/123/status/
```

#### Ответ

```json
{
  "success": true,
  "task_id": "123",
  "status": "running",
  "progress": 45,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:30Z",
  "started_at": "2024-01-01T12:00:05Z",
  "completed_at": null,
  "error_message": "",
  "is_finished": false,
  "is_active": true,
  "duration_seconds": 25.5,
  "metadata": {
    "source_type": "file",
    "target_format": "gif",
    "original_filename": "video.mp4",
    "file_size": 1024000,
    "conversion_params": { ... }
  }
}
```

#### Статусы задач

- `queued` - Задача в очереди
- `running` - Задача выполняется
- `done` - Задача завершена успешно
- `failed` - Задача завершилась с ошибкой

---

## 3. Получение Результата Задачи

### GET `/api/tasks/{task_id}/result/`

Возвращает информацию о результате выполненной задачи.

```bash
curl http://your-domain.com/api/tasks/123/result/
```

#### Ответ для успешной задачи

```json
{
  "success": true,
  "task_id": "123",
  "status": "done",
  "result": {
    "output_url": "/media/results/task_123_result.gif",
    "download_url": "/api/tasks/123/download/",
    "filename": "task_123_result.gif",
    "file_size": 512000,
    "format": "gif",
    "original_filename": "video.mp4",
    "conversion_params": { ... }
  },
  "completed_at": "2024-01-01T12:01:00Z",
  "duration_seconds": 60.0
}
```

#### Ответ для неуспешной задачи

```json
{
  "success": false,
  "task_id": "123",
  "status": "failed",
  "error_message": "Ошибка при конвертации файла",
  "completed_at": "2024-01-01T12:00:45Z"
}
```

---

## 4. Скачивание Результата

### GET `/api/tasks/{task_id}/download/`

Скачивает готовый файл результата конвертации.

```bash
curl -O http://your-domain.com/api/tasks/123/download/
```

#### Ответ

Бинарный файл с заголовками:
- `Content-Type`: соответствующий MIME-тип
- `Content-Disposition`: attachment с именем файла
- `Content-Length`: размер файла

---

## 5. Список Всех Задач

### GET `/api/tasks/`

Получает список всех задач с поддержкой пагинации и фильтрации.

```bash
# Базовый запрос
curl http://your-domain.com/api/tasks/

# С параметрами
curl "http://your-domain.com/api/tasks/?page=1&per_page=10&status=done&format=gif&order=-created_at"
```

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|----------|
| `page` | Integer | Номер страницы (по умолчанию: 1) |
| `per_page` | Integer | Количество на страницу (по умолчанию: 20, макс: 100) |
| `status` | String | Фильтр по статусу (`queued`, `running`, `done`, `failed`) |
| `format` | String | Фильтр по целевому формату |
| `order` | String | Сортировка (`created_at`, `-created_at`, `updated_at`, `-updated_at`, `status`, `-status`) |

#### Ответ

```json
{
  "success": true,
  "tasks": [
    {
      "task_id": "123",
      "status": "done",
      "progress": 100,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:01:00Z",
      "started_at": "2024-01-01T12:00:05Z",
      "completed_at": "2024-01-01T12:01:00Z",
      "error_message": "",
      "target_format": "gif",
      "original_filename": "video.mp4",
      "file_size": 1024000,
      "duration_seconds": 55.0,
      "api_urls": {
        "status": "/api/tasks/123/status/",
        "result": "/api/tasks/123/result/",
        "download": "/api/tasks/123/download/"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_previous": false
  }
}
```

---

## 6. Пакетное Скачивание

### GET/POST `/api/tasks/batch-download/`

Скачивает результаты нескольких задач в виде ZIP-архива.

#### Вариант 1: GET запрос

```bash
curl -O "http://your-domain.com/api/tasks/batch-download/?task_ids=1,2,3,4"
```

#### Вариант 2: POST запрос

```bash
curl -X POST http://your-domain.com/api/tasks/batch-download/ \
  -H "Content-Type: application/json" \
  -d '{"task_ids": [1, 2, 3, 4]}' \
  -O
```

#### Ответ

ZIP файл с заголовками:
- `Content-Type`: application/zip
- `Content-Disposition`: attachment с именем архива
- `X-Total-Tasks`: общее количество запрошенных задач
- `X-Successful-Tasks`: количество успешно включенных задач
- `X-Files-Count`: количество файлов в архиве

---

## Коды Ошибок

| HTTP Код | Описание |
|----------|----------|
| 200 | Успешный запрос |
| 400 | Некорректные параметры запроса |
| 404 | Задача не найдена |
| 500 | Внутренняя ошибка сервера |

## Примеры Использования

### Полный цикл работы с задачей

```bash
# 1. Создание задачи
TASK_ID=$(curl -X POST http://your-domain.com/api/tasks/create/ \
  -F "file=@video.mp4" \
  -F "format=gif" \
  -F "width=480" | jq -r '.task_id')

# 2. Проверка статуса
curl http://your-domain.com/api/tasks/$TASK_ID/status/

# 3. Ожидание завершения и скачивание
while true; do
  STATUS=$(curl -s http://your-domain.com/api/tasks/$TASK_ID/status/ | jq -r '.status')
  if [ "$STATUS" = "done" ]; then
    curl -O http://your-domain.com/api/tasks/$TASK_ID/download/
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "Task failed"
    break
  fi
  sleep 5
done
```

### Пакетное скачивание всех GIF файлов

```bash
# Получить все задачи со статусом done и форматом gif
TASK_IDS=$(curl -s "http://your-domain.com/api/tasks/?status=done&format=gif&per_page=50" | \
  jq -r '.tasks[].task_id' | tr '\n' ',' | sed 's/,$//')

# Скачать ZIP архив
curl -O "http://your-domain.com/api/tasks/batch-download/?task_ids=$TASK_IDS"
```

## Ограничения

- Максимальный размер загружаемого файла: 500 МБ
- Максимальное количество задач для пакетного скачивания: 50
- Максимальное количество задач на страницу: 100
- Поддерживаемые форматы входных файлов: MP4, AVI, MOV, WEBM и другие видеоформаты
- Поддерживаемые выходные форматы: GIF (другие форматы можно добавить)

## Рекомендации для Production

1. **Аутентификация**: Добавьте систему API ключей или JWT токенов
2. **Rate Limiting**: Ограничьте количество запросов от одного IP
3. **Celery**: Замените threading на Celery для обработки задач
4. **Monitoring**: Добавьте логирование и мониторинг API
5. **Кэширование**: Используйте Redis для кэширования статусов задач
6. **Хранилище**: Рассмотрите использование S3 или аналогов для хранения файлов
7. **Очистка**: Настройте автоматическую очистку старых файлов
