# Тестирование функциональности STT системы

Этот каталог содержит комплексную систему тестирования для проверки функциональности Speech-to-Text (STT) согласно **шагу 8** из плана разработки.

## 📋 Содержание

### 🎯 Что тестируется

1. **Короткие тест-клипы RU/EN (15-60 сек)** — проверка точности и выбора языка
2. **Длинные файлы (5-10 мин)** — проверка сегментации, стабильности, прогресса
3. **UI функциональность** — drag-and-drop, прогресс-бар, скачивание всех форматов
4. **Celery + API** — автотесты через pytest для асинхронных задач

### 📁 Файлы в каталоге

- `run_all_tests.py` — **главный скрипт запуска всех тестов**
- `test_audio_generator.py` — генератор тестовых аудиофайлов
- `test_stt_functionality.py` — тесты API и функциональности STT
- `test_ui_functionality.py` — тесты пользовательского интерфейса (Selenium)
- `test_celery_api.py` — тесты Celery + API через pytest
- `requirements_tests.txt` — зависимости для тестов
- `README.md` — этот файл с инструкциями

## 🚀 Быстрый запуск

### 1. Установка зависимостей

```bash
# Установка всех тестовых зависимостей
pip install -r tests/requirements_tests.txt

# Для минимального запуска (без UI тестов)
pip install pytest pytest-django pydub requests
```

### 2. Запуск всех тестов

```bash
# Полный запуск всех тестов
python tests/run_all_tests.py

# Запуск без UI тестов (если нет Selenium)
python tests/run_all_tests.py --skip-ui

# Запуск только API и базовые тесты
python tests/run_all_tests.py --skip-ui --skip-celery
```

### 3. Просмотр результатов

После выполнения тестов будут созданы:
- `test_results.log` — детальный лог выполнения
- `test_report_YYYYMMDD_HHMMSS.json` — JSON отчет с результатами
- `celery_test_results.xml` — JUnit XML отчет для Celery тестов

## 📊 Детальное описание тестов

### 🎵 Тест 1: Генерация и обработка коротких аудиоклипов

**Что проверяется:**
- Точность распознавания речи для русского языка
- Точность распознавания речи для английского языка
- Корректный выбор языка распознавания
- Обработка файлов разной длительности (15, 30, 45, 60 сек)

**Файлы:** `test_audio_generator.py`, `test_stt_functionality.py`

```bash
# Запуск только этих тестов
python -m pytest tests/test_stt_functionality.py::STTFunctionalityTest::test_01_short_audio_ru_processing -v
python -m pytest tests/test_stt_functionality.py::STTFunctionalityTest::test_02_short_audio_en_processing -v
```

### 📈 Тест 2: Длинные файлы и сегментация

**Что проверяется:**
- Стабильность обработки файлов 5-10 минут
- Корректная сегментация на части
- Прогресс обработки длинных файлов
- Асинхронная обработка через Celery

**Файлы:** `test_stt_functionality.py`

```bash
# Запуск теста длинных файлов
python -m pytest tests/test_stt_functionality.py::STTFunctionalityTest::test_03_long_file_processing -v
```

### 🖥️ Тест 3: UI функциональность

**Что проверяется:**
- Drag-and-drop загрузка файлов
- Отображение прогресс-бара
- Скачивание результатов в разных форматах (TXT, JSON, SRT)
- Интеграционный workflow: загрузка → обработка → скачивание

**Файлы:** `test_ui_functionality.py`

**Требования:** Selenium WebDriver

```bash
# Установка Selenium
pip install selenium webdriver-manager

# Запуск UI тестов
python -m pytest tests/test_ui_functionality.py -v

# Или через главный скрипт
python tests/run_all_tests.py --skip-celery  # только UI тесты
```

### ⚙️ Тест 4: Celery + API автотесты

**Что проверяется:**
- Создание и выполнение асинхронных задач
- Проверка статуса задач через API
- Отмена задач
- Маршрутизация по очередям
- Обработка ошибок в задачах

**Файлы:** `test_celery_api.py`

```bash
# Запуск Celery тестов через pytest
python -m pytest tests/test_celery_api.py -v

# Или через главный скрипт
python tests/run_all_tests.py --skip-ui  # только API и Celery тесты
```

## 🔧 Конфигурация тестов

### Переменные окружения

```bash
# Django настройки
export DJANGO_SETTINGS_MODULE=converter_site.settings

# Тестовые настройки (опционально)
export TEST_AUDIO_DIR=/path/to/test/audio
export TEST_OUTPUT_DIR=/path/to/test/output
```

### Файл конфигурации

Создайте `test_config.json` для кастомизации:

```json
{
  "audio_generation": {
    "max_file_duration": 300,
    "test_languages": ["ru", "en"],
    "quality_levels": ["low", "medium", "high"]
  },
  "ui_tests": {
    "browser": "chrome",
    "headless": true,
    "timeout": 30
  },
  "api_tests": {
    "base_url": "http://localhost:8000",
    "timeout": 120
  }
}
```

Запуск с конфигурацией:
```bash
python tests/run_all_tests.py --config test_config.json
```

## 📈 Интерпретация результатов

### Критерии успешности

- **✅ Отличный результат (≥90%):** Система готова к продакшену
- **👍 Хороший результат (≥75%):** Рекомендуется устранить оставшиеся проблемы
- **⚠️ Средний результат (≥50%):** Требуется доработка функциональности
- **🚨 Низкий результат (<50%):** Необходима серьезная отладка системы

### Пример итогового отчета

```
📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ
======================================
⏱️ Общее время выполнения: 245.3 сек
📈 Всего тестов: 23
✅ Успешных: 21
❌ Неудачных: 1
🚨 Ошибок: 1
🎯 Общая успешность: 91.3%

📋 Детали по этапам:
   ✅ Генерация тестовых данных: success
     📁 Создано файлов: 14
   ✅ API тесты: 85.7% успешность
     ⏱️ Время: 125.4 сек
   ✅ UI тесты: 100.0% успешность
     ⏱️ Время: 89.1 сек
   ✅ Celery тесты: код выхода 0
     ⏱️ Время: 30.8 сек
```

## 🐛 Устранение неполадок

### Проблема: Не установлен Selenium

```bash
pip install selenium webdriver-manager
```

Или запускайте тесты с `--skip-ui`

### Проблема: Не запущен Redis для Celery

```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Windows (Docker)
docker run -d -p 6379:6379 redis
```

### Проблема: Ошибки с аудиофайлами

Убедитесь, что установлены аудиозависимости:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg libsndfile1

# macOS
brew install ffmpeg libsndfile

# Windows
# Скачайте FFmpeg и добавьте в PATH
```

### Проблема: Django settings не найдены

```bash
export DJANGO_SETTINGS_MODULE=converter_site.settings
# или создайте .env файл с этой переменной
```

## 📋 Чеклист перед коммитом

- [ ] Все тесты проходят (`python tests/run_all_tests.py`)
- [ ] Успешность ≥ 85%
- [ ] Нет критических ошибок в логах
- [ ] UI тесты проходят (если используется веб-интерфейс)
- [ ] Celery задачи выполняются корректно

## 🤝 Участие в разработке

Для добавления новых тестов:

1. **API тесты:** добавляйте в `test_stt_functionality.py`
2. **UI тесты:** добавляйте в `test_ui_functionality.py`
3. **Celery тесты:** добавляйте в `test_celery_api.py`
4. **Тестовые данные:** расширяйте `test_audio_generator.py`

Всегда добавляйте документацию и примеры использования для новых тестов.

---

**📞 Поддержка:** При возникновении проблем проверьте логи в `test_results.log` и обратитесь к детальному JSON отчету.
