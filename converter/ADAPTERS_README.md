# Слой адаптеров для конвертеров файлов

Этот документ описывает архитектуру и использование нового слоя адаптеров для различных типов конвертеров файлов.

## Архитектура

Слой адаптеров организован по принципу адаптера (Adapter Pattern) и обеспечивает единообразный интерфейс для работы с различными типами файлов и движками конвертации.

### Основные компоненты

#### 1. BaseEngine (базовый класс)
Абстрактный базовый класс, определяющий общий интерфейс для всех адаптеров.

**Ключевые методы:**
- `convert()` - основной метод конвертации
- `get_supported_formats()` - получение поддерживаемых форматов
- `validate_input()` - валидация входного файла
- `check_dependencies()` - проверка зависимостей
- `get_file_info()` - получение информации о файле

#### 2. Конкретные адаптеры

##### VideoEngine
Адаптер для конвертации видео файлов. Использует существующую логику `VideoConverter`.

**Поддерживаемые входные форматы:**
- mp4, avi, mov, mkv, webm, flv, m4v, wmv, mpg, mpeg, 3gp, ogg, ogv

**Поддерживаемые выходные форматы:**
- gif (полностью реализовано)
- mp4, webm, avi (планируется)

**Пример использования:**
```python
from converter.adapters import VideoEngine

# Создание адаптера
video_engine = VideoEngine(use_moviepy=True)

# Проверка доступности
if video_engine.is_available():
    # Конвертация
    result = video_engine.convert(
        input_file=video_file,
        output_path='output.gif',
        width=480,
        fps=15,
        start_time=0,
        end_time=10
    )
    
    if result.success:
        print(f"Файл сохранен: {result.output_path}")
    else:
        print(f"Ошибка: {result.error_message}")
```

##### ImageEngine
Адаптер для конвертации изображений (базовая реализация).

**Поддерживаемые форматы:**
- Входные: jpg, jpeg, png, gif, bmp, tiff, webp, svg, ico, psd, raw, heic, heif
- Выходные: jpg, jpeg, png, gif, bmp, tiff, webp, ico

##### AudioEngine
Адаптер для конвертации аудио файлов (базовая реализация).

**Поддерживаемые форматы:**
- Входные: mp3, wav, flac, ogg, aac, m4a, wma, opus, amr, ra, au, aiff, caf
- Выходные: mp3, wav, flac, ogg, aac, m4a, opus

##### DocumentEngine
Адаптер для конвертации документов (базовая реализация).

**Поддерживаемые форматы:**
- Входные: pdf, doc, docx, rtf, odt, txt, md, html, xls, xlsx, ods, csv, ppt, pptx, odp, epub, mobi, fb2, djvu, tex, latex
- Выходные: pdf, docx, rtf, odt, txt, md, html, xlsx, ods, csv, pptx, odp, epub

##### ArchiveEngine
Адаптер для работы с архивами (базовая реализация).

**Поддерживаемые форматы:**
- Входные: zip, rar, 7z, tar, tar.gz, tar.bz2, tar.xz, gz, bz2, xz, lzma, lz4, zst, cab, arj, lzh, ace, iso, dmg
- Выходные: zip, 7z, tar, tar.gz, tar.bz2, tar.xz

#### 3. EngineManager (менеджер адаптеров)
Центральный компонент для управления всеми адаптерами.

**Основные возможности:**
- Автоматическое определение типа файла
- Создание и кэширование адаптеров
- Универсальный интерфейс для конвертации
- Получение статуса всех адаптеров

**Пример использования:**
```python
from converter.adapters import engine_manager

# Автоматическая конвертация
result = engine_manager.convert_file(
    input_file=some_file,
    output_path='output.gif',
    width=640,
    fps=20
)

# Получение статуса всех адаптеров
status = engine_manager.get_engine_status()

# Получение поддерживаемых форматов
formats = engine_manager.get_supported_formats()
```

## Интеграция с Django Views

### Новые view-функции

В файле `converter/adapters_views.py` представлены примеры интеграции адаптеров с Django:

1. **`convert_with_adapters_view`** - универсальная конвертация через менеджер
2. **`video_convert_adapter_view`** - специализированная конвертация видео
3. **`engine_status_view`** - получение статуса адаптеров
4. **`detect_file_type_view`** - определение типа файла
5. **`legacy_video_convert_view`** - обратная совместимость

### Использование в существующих views

Пример модификации существующих view-функций для использования новых адаптеров:

```python
# Вместо прямого использования VideoConverter
from converter.utils import VideoConverter
converter = VideoConverter(use_moviepy=False)

# Используем VideoEngine
from converter.adapters import VideoEngine
video_engine = VideoEngine(use_moviepy=False)
```

## Расширение функциональности

### Добавление нового адаптера

1. Создайте класс, наследующий от `BaseEngine`:
```python
from .base import BaseEngine, ConversionResult

class MyEngine(BaseEngine):
    def convert(self, input_file, output_path, **kwargs):
        # Реализация конвертации
        pass
    
    def get_supported_formats(self):
        return {
            'input': ['format1', 'format2'],
            'output': ['format3', 'format4']
        }
    
    def validate_input(self, input_file):
        # Валидация входного файла
        pass
```

2. Зарегистрируйте адаптер в `EngineManager`:
```python
# В __init__ метода EngineManager
self._engine_classes['my_type'] = MyEngine
```

3. Добавьте mapping форматов в `detect_engine_type`:
```python
# В extension_mapping
'myformat': 'my_type'
```

### Добавление новой функциональности в существующий адаптер

Наследуйте от существующего адаптера и расширьте его:

```python
class ExtendedVideoEngine(VideoEngine):
    def convert_to_webm(self, input_file, output_path, **kwargs):
        # Дополнительная функциональность
        pass
```

## Обратная совместимость

Новый слой адаптеров полностью совместим с существующим кодом:

1. **VideoEngine** использует существующий `VideoConverter` внутри себя
2. Все существующие параметры конвертации поддерживаются
3. Результаты конвертации сохраняются в том же формате
4. Предоставлены wrapper-функции для старого API

## Тестирование

### Проверка доступности адаптеров

```python
from converter.adapters import engine_manager

# Проверка статуса всех адаптеров
status = engine_manager.get_engine_status()
for engine_type, info in status.items():
    print(f"{engine_type}: {'доступен' if info['available'] else 'недоступен'}")
    print(f"  Зависимости: {info['dependencies']}")
```

### Тестирование конвертации

```python
from converter.adapters import VideoEngine
import tempfile

def test_video_conversion():
    engine = VideoEngine(use_moviepy=True)
    
    if not engine.is_available():
        print("Адаптер видео недоступен")
        return
    
    with tempfile.NamedTemporaryFile(suffix='.gif') as tmp:
        result = engine.convert(
            input_file='test_video.mp4',
            output_path=tmp.name,
            width=320,
            fps=10
        )
        
        if result.success:
            print("Тест прошел успешно!")
        else:
            print(f"Тест провален: {result.error_message}")
```

## Планы развития

1. **Полная реализация ImageEngine** - добавление поддержки Pillow/PIL
2. **Полная реализация AudioEngine** - интеграция с pydub/librosa
3. **Полная реализация DocumentEngine** - интеграция с pypandoc/LibreOffice
4. **Полная реализация ArchiveEngine** - поддержка zipfile/tarfile/py7zr
5. **Асинхронная конвертация** - интеграция с Celery
6. **Пакетная обработка** - конвертация множества файлов
7. **Потоковая обработка** - обработка больших файлов по частям
8. **Плагинная архитектура** - загрузка адаптеров из внешних модулей

## Заключение

Новый слой адаптеров обеспечивает:
- **Единообразный интерфейс** для всех типов конвертации
- **Расширяемость** для добавления новых форматов и движков
- **Обратную совместимость** с существующим кодом
- **Простоту использования** через менеджер адаптеров
- **Надежность** благодаря проверке зависимостей и валидации

Этот подход позволяет легко добавлять новые типы файлов и движки конвертации, сохраняя при этом простоту использования и надежность системы.
