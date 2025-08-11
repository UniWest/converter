#!/usr/bin/env python
import sys
import tempfile
"""
Простые тесты для проверки работы слоя адаптеров.
Запустите этот файл для проверки базовой функциональности.
"""

import os

# Добавляем путь к проекту
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"Ошибка при инициализации Django: {e}")
    sys.exit(1)

# Импорт адаптеров
try:
    from converter.adapters import engine_manager, VideoEngine, ImageEngine, AudioEngine, DocumentEngine, ArchiveEngine
    from converter.adapters.base import ConversionResult
    print("[OK] Адаптеры успешно импортированы")
except ImportError as e:
    print(f"[X] Ошибка импорта адаптеров: {e}")
    sys.exit(1)


def test_engine_manager():
    """Тестирование менеджера адаптеров."""
    print("\n=== Тестирование EngineManager ===")
    
    # Тест создания адаптеров
    video_engine = engine_manager.get_engine('video')
    assert video_engine is not None, "VideoEngine должен создаваться"
    print("✓ VideoEngine создан")
    
    image_engine = engine_manager.get_engine('image')
    assert image_engine is not None, "ImageEngine должен создаваться"
    print("✓ ImageEngine создан")
    
    # Тест определения типа файла
    assert engine_manager.detect_engine_type('video.mp4') == 'video'
    assert engine_manager.detect_engine_type('image.jpg') == 'image'
    assert engine_manager.detect_engine_type('audio.mp3') == 'audio'
    assert engine_manager.detect_engine_type('document.pdf') == 'document'
    assert engine_manager.detect_engine_type('archive.zip') == 'archive'
    assert engine_manager.detect_engine_type('archive.tar.gz') == 'archive'
    print("✓ Определение типа файла работает корректно")
    
    # Тест получения статуса
    status = engine_manager.get_engine_status()
    assert isinstance(status, dict), "Статус должен быть словарем"
    assert 'video' in status, "Статус должен содержать видео адаптер"
    print("✓ Получение статуса работает")
    
    # Тест получения поддерживаемых форматов
    formats = engine_manager.get_supported_formats()
    assert isinstance(formats, dict), "Форматы должны быть словарем"
    print("✓ Получение поддерживаемых форматов работает")


def test_video_engine():
    """Тестирование VideoEngine."""
    print("\n=== Тестирование VideoEngine ===")
    
    # Создание адаптера
    video_engine = VideoEngine(use_moviepy=True)
    print("✓ VideoEngine создан")
    
    # Проверка поддерживаемых форматов
    formats = video_engine.get_supported_formats()
    assert 'input' in formats and 'output' in formats
    assert 'mp4' in formats['input']
    assert 'gif' in formats['output']
    print("✓ Поддерживаемые форматы определены корректно")
    
    # Проверка валидации
    assert video_engine.validate_input(type('MockFile', (), {'name': 'test.mp4'})())
    assert not video_engine.validate_input(type('MockFile', (), {'name': 'test.txt'})())
    print("✓ Валидация входных файлов работает")
    
    # Проверка зависимостей
    deps = video_engine.check_dependencies()
    assert isinstance(deps, dict)
    print(f"✓ Проверка зависимостей: {deps}")


def test_other_engines():
    """Тестирование остальных адаптеров."""
    print("\n=== Тестирование остальных адаптеров ===")
    
    engines = [
        ('image', ImageEngine),
        ('audio', AudioEngine),
        ('document', DocumentEngine),
        ('archive', ArchiveEngine)
    ]
    
    for engine_name, engine_class in engines:
        print(f"\nТестирование {engine_name}:")
        
        # Создание адаптера
        engine = engine_class()
        print(f"  ✓ {engine_class.__name__} создан")
        
        # Проверка форматов
        formats = engine.get_supported_formats()
        assert 'input' in formats and 'output' in formats
        assert len(formats['input']) > 0
        assert len(formats['output']) > 0
        print(f"  ✓ Форматы: {len(formats['input'])} входных, {len(formats['output'])} выходных")
        
        # Проверка зависимостей
        deps = engine.check_dependencies()
        assert isinstance(deps, dict)
        print(f"  ✓ Зависимости проверены: {list(deps.keys())}")


def test_conversion_result():
    """Тестирование ConversionResult."""
    print("\n=== Тестирование ConversionResult ===")
    
    # Успешный результат
    result = ConversionResult(
        success=True,
        output_path="/path/to/output.gif",
        metadata={"duration": 10}
    )
    assert result.success is True
    assert result.output_path == "/path/to/output.gif"
    assert result.metadata["duration"] == 10
    print("✓ Успешный результат создан корректно")
    
    # Результат с ошибкой
    error_result = ConversionResult(
        success=False,
        error_message="Test error"
    )
    assert error_result.success is False
    assert error_result.error_message == "Test error"
    assert error_result.metadata == {}  # Должен быть пустой словарь по умолчанию
    print("✓ Результат с ошибкой создан корректно")


def print_engine_status():
    """Печатает подробный статус всех адаптеров."""
    print("\n=== Подробный статус адаптеров ===")
    
    status = engine_manager.get_engine_status()
    
    for engine_type, info in status.items():
        print(f"\n{engine_type.upper()}:")
        print(f"  Доступен: {'Да' if info['available'] else 'Нет'}")
        
        print("  Зависимости:")
        for dep_name, dep_status in info['dependencies'].items():
            status_text = "✓" if dep_status else "✗"
            print(f"    {status_text} {dep_name}")
        
        formats = info['supported_formats']
        print(f"  Входных форматов: {len(formats['input'])}")
        print(f"  Выходных форматов: {len(formats['output'])}")


def main():
    """Главная функция тестирования."""
    print("Запуск тестов слоя адаптеров конвертеров")
    print("=" * 50)
    
    try:
        test_conversion_result()
        test_engine_manager()
        test_video_engine()
        test_other_engines()
        print_engine_status()
        
        print("\n" + "=" * 50)
        print("✅ Все тесты прошли успешно!")
        print("\n📋 Результаты:")
        print("- Базовая функциональность адаптеров работает")
        print("- Менеджер адаптеров функционирует корректно")
        print("- VideoEngine интегрирован с существующим VideoConverter")
        print("- Остальные адаптеры готовы к расширению функциональности")
        
    except Exception as e:
        print(f"\n❌ Тест провален с ошибкой: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
