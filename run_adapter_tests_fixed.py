#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Главный скрипт для запуска всех тестов адаптеров конвертации.
Запускает unit-тесты, интеграционные тесты и тесты с небольшими файлами.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Настройка Django
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"Ошибка при инициализации Django: {e}")
    sys.exit(1)


def print_header(text):
    """Печатает заголовок раздела."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_separator():
    """Печатает разделитель."""
    print("-" * 70)


def check_dependencies():
    """Проверяет доступность необходимых зависимостей."""
    print_header("ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    
    dependencies = {
        'Django': 'django',
        'PIL/Pillow': 'PIL',
        'unittest': 'unittest',
    }
    
    available = {}
    
    for name, module in dependencies.items():
        try:
            __import__(module)
            available[name] = True
            print(f"[OK] {name} - доступен")
        except ImportError:
            available[name] = False
            print(f"[X] {name} - НЕ доступен")
    
    # Проверяем внешние инструменты
    external_tools = {
        'ffmpeg': 'видео конвертация',
        'git': 'система контроля версий'
    }
    
    print("\nВнешние инструменты:")
    for tool, description in external_tools.items():
        import shutil
        if shutil.which(tool):
            print(f"[OK] {tool} - доступен ({description})")
            available[tool] = True
        else:
            print(f"[X] {tool} - НЕ доступен ({description})")
            available[tool] = False
    
    return available


def run_test_file(test_file, description):
    """Запускает отдельный файл тестов."""
    print_separator()
    print(f"Запуск: {description}")
    print(f"   Файл: {test_file}")
    print_separator()
    
    if not Path(test_file).exists():
        print(f"[FAIL] Файл тестов не найден: {test_file}")
        return False
    
    start_time = time.time()
    
    try:
        # Запускаем тест как subprocess
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            cwd=project_path
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"[OK] {description} - УСПЕШНО ({duration:.2f}с)")
            return True
        else:
            print(f"[FAIL] {description} - ПРОВАЛ (код: {result.returncode}, {duration:.2f}с)")
            return False
            
    except Exception as e:
        print(f"[ERROR] Ошибка запуска {description}: {e}")
        return False


def run_quick_validation():
    """Быстрая проверка базовой функциональности."""
    print_header("БЫСТРАЯ ВАЛИДАЦИЯ")
    
    try:
        from converter.adapters import engine_manager
        from converter.adapters.base import ConversionResult
        
        print("[OK] Импорт адаптеров успешен")
        
        # Проверка создания менеджера
        manager = engine_manager
        print("[OK] Менеджер адаптеров создан")
        
        # Проверка получения адаптеров
        video_engine = manager.get_engine('video')
        image_engine = manager.get_engine('image')
        
        if video_engine and image_engine:
            print("[OK] Основные адаптеры доступны")
        else:
            print("[WARN] Некоторые адаптеры недоступны")
        
        # Проверка определения типов файлов
        test_files = {
            'video.mp4': 'video',
            'image.jpg': 'image',
            'audio.mp3': 'audio'
        }
        
        for filename, expected in test_files.items():
            detected = manager.detect_engine_type(filename)
            if detected == expected:
                print(f"[OK] {filename} → {detected}")
            else:
                print(f"[WARN] {filename} → {detected} (ожидался {expected})")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Ошибка валидации: {e}")
        return False


def generate_test_report(results, total_time):
    """Генерирует итоговый отчет о тестах."""
    print_header("ИТОГОВЫЙ ОТЧЕТ")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    failed_tests = total_tests - passed_tests
    
    print(f"Общая статистика:")
    print(f"   • Всего тест-наборов: {total_tests}")
    print(f"   • Успешно: {passed_tests}")
    print(f"   • Провалено: {failed_tests}")
    print(f"   • Процент успеха: {passed_tests/total_tests*100:.1f}%")
    
    print(f"\nДетализация:")
    for test_name, success in results.items():
        status = "[OK] ПРОШЕЛ" if success else "[FAIL] ПРОВАЛЕН"
        print(f"   • {test_name}: {status}")
    
    print(f"\nВремя тестирования: {total_time:.2f} секунд")
    
    if all(results.values()):
        print(f"\n[SUCCESS] ВСЕ ТЕСТЫ АДАПТЕРОВ ПРОШЛИ УСПЕШНО!")
        print("Требуется доработка адаптеров.")
        return True
    else:
        print(f"\n[WARN] Некоторые тесты провалились. Требуется внимание.")
        print("Требуется доработка адаптеров.")
        return False


def main():
    """Главная функция."""
    print_header("ЗАПУСК ТЕСТИРОВАНИЯ АДАПТЕРОВ КОНВЕРТАЦИИ")
    print("Комплексное тестирование unit-тестов и интеграционных тестов")
    
    start_time = time.time()
    
    # 1. Проверка зависимостей
    available_deps = check_dependencies()
    
    # 2. Быстрая валидация
    validation_ok = run_quick_validation()
    if not validation_ok:
        print("[FAIL] Быстрая валидация провалилась, прерываем тестирование")
        return 1
    
    # 3. Запуск тестов
    tests_to_run = [
        ('test_adapters.py', 'Базовые тесты адаптеров'),
        ('test_adapter_units.py', 'Unit-тесты адаптеров'),
        ('test_adapter_integrations.py', 'Интеграционные тесты'),
        ('test_small_files.py', 'Тесты с небольшими файлами'),
    ]
    
    results = {}
    
    for test_file, description in tests_to_run:
        if Path(test_file).exists():
            success = run_test_file(test_file, description)
            results[description] = success
        else:
            print(f"[SKIP] Файл {test_file} не найден")
            results[description] = False
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 4. Генерация отчета
    success = generate_test_report(results, total_time)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
