# -*- coding: utf-8 -*-
"""
Проверка готовности окружения для файлового конвертера
Аналог системы проверки Convertio для всех необходимых компонентов
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path

def check_python_packages():
    """Проверка Python пакетов из requirements.txt"""
    print("🐍 Проверка Python пакетов:")
    print("-" * 40)
    
    required_packages = [
        'django', 'celery', 'redis', 'Wand', 'magic', 'cv2', 
        'numpy', 'PIL', 'pydub', 'docx', 'openpyxl', 'pptx'
    ]
    
    status = {}
    for package in required_packages:
        try:
            if package == 'magic':
                import magic
                status[package] = "✅ ОК"
            elif package == 'cv2':
                import cv2
                status[package] = "✅ ОК" 
            elif package == 'PIL':
                from PIL import Image
                status[package] = "✅ ОК"
            else:
                importlib.import_module(package)
                status[package] = "✅ ОК"
        except ImportError:
            status[package] = "❌ НЕ НАЙДЕН"
    
    for package, result in status.items():
        print(f"  {package:15} | {result}")
    
    return all("✅" in status for status in status.values())

def check_external_binaries():
    """Проверка внешних бинарников"""
    print("\n🔧 Проверка внешних утилит:")
    print("-" * 40)
    
    from converter_settings import BINARY_PATHS, check_binary_availability
    
    status = check_binary_availability()
    all_ok = True
    
    for name, info in status.items():
        if info['available'] and info['executable']:
            result = "✅ ОК"
        else:
            result = "❌ НЕ НАЙДЕН"
            all_ok = False
        
        print(f"  {name:15} | {result}")
        if not info['available']:
            print(f"     Путь: {info['path']}")
    
    return all_ok

def check_redis_connection():
    """Проверка подключения к Redis"""
    print("\n📡 Проверка Redis:")
    print("-" * 40)
    
    try:
        import redis
        from converter_settings import REDIS_URL
        
        # Парсим URL Redis
        if REDIS_URL.startswith('redis://'):
            parts = REDIS_URL.replace('redis://', '').split('/')
            host_port = parts[0].split(':')
            host = host_port[0] if host_port[0] else 'localhost'
            port = int(host_port[1]) if len(host_port) > 1 else 6379
            db = int(parts[1]) if len(parts) > 1 else 0
        else:
            host, port, db = 'localhost', 6379, 0
        
        r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        r.ping()
        print("  Redis соединение | ✅ ОК")
        return True
        
    except Exception as e:
        print(f"  Redis соединение | ❌ ОШИБКА: {e}")
        return False

def check_directories():
    """Проверка и создание необходимых директорий"""
    print("\n📁 Проверка директорий:")
    print("-" * 40)
    
    from converter_settings import TEMP_DIRS
    
    all_ok = True
    for dir_name, dir_path in TEMP_DIRS.items():
        path = Path(dir_path)
        
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"  {dir_name:15} | ✅ СОЗДАН: {dir_path}")
            except Exception as e:
                print(f"  {dir_name:15} | ❌ ОШИБКА: {e}")
                all_ok = False
        else:
            print(f"  {dir_name:15} | ✅ СУЩЕСТВУЕТ: {dir_path}")
    
    return all_ok

def check_disk_space():
    """Проверка свободного места на диске"""
    print("\n💾 Проверка свободного места:")
    print("-" * 40)
    
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        
        gb = 1024 ** 3
        print(f"  Всего места     | {total // gb:3d} GB")
        print(f"  Использовано    | {used // gb:3d} GB") 
        print(f"  Свободно        | {free // gb:3d} GB")
        
        if free > 5 * gb:  # Минимум 5GB свободно
            print("  Статус          | ✅ ДОСТАТОЧНО")
            return True
        else:
            print("  Статус          | ⚠️  МАЛО МЕСТА")
            return False
            
    except Exception as e:
        print(f"  Ошибка проверки | ❌ {e}")
        return False

def run_basic_tests():
    """Базовые тесты функциональности"""
    print("\n🧪 Базовые тесты:")
    print("-" * 40)
    
    tests_passed = 0
    total_tests = 4
    
    # Тест 1: ImageMagick
    try:
        from converter_settings import BINARY_PATHS
        magick_path = BINARY_PATHS['magick']
        result = subprocess.run([magick_path, '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ImageMagick      | ✅ ОК")
            tests_passed += 1
        else:
            print("  ImageMagick      | ❌ ОШИБКА")
    except Exception:
        print("  ImageMagick      | ❌ НЕ РАБОТАЕТ")
    
    # Тест 2: FFmpeg
    try:
        ffmpeg_path = BINARY_PATHS['ffmpeg']
        result = subprocess.run([ffmpeg_path, '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  FFmpeg           | ✅ ОК")
            tests_passed += 1
        else:
            print("  FFmpeg           | ❌ ОШИБКА")
    except Exception:
        print("  FFmpeg           | ❌ НЕ РАБОТАЕТ")
    
    # Тест 3: LibreOffice
    try:
        soffice_path = BINARY_PATHS['soffice']
        result = subprocess.run([soffice_path, '--help'], 
                              capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print("  LibreOffice      | ✅ ОК")
            tests_passed += 1
        else:
            print("  LibreOffice      | ❌ ОШИБКА")
    except Exception:
        print("  LibreOffice      | ❌ НЕ РАБОТАЕТ")
    
    # Тест 4: 7-Zip  
    try:
        zip_path = BINARY_PATHS['7z']
        result = subprocess.run([zip_path], 
                              capture_output=True, text=True, timeout=10)
        # 7z возвращает код 1 при запуске без параметров, но это нормально
        if result.returncode in [0, 1]:
            print("  7-Zip            | ✅ ОК")
            tests_passed += 1
        else:
            print("  7-Zip            | ❌ ОШИБКА")
    except Exception:
        print("  7-Zip            | ❌ НЕ РАБОТАЕТ")
    
    return tests_passed, total_tests

def main():
    """Основная функция проверки окружения"""
    print("🚀 ПРОВЕРКА ОКРУЖЕНИЯ ФАЙЛОВОГО КОНВЕРТЕРА")
    print("=" * 50)
    
    checks = [
        ("Python пакеты", check_python_packages),
        ("Внешние утилиты", check_external_binaries), 
        ("Redis соединение", check_redis_connection),
        ("Директории", check_directories),
        ("Место на диске", check_disk_space),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Ошибка при проверке '{name}': {e}")
            results.append((name, False))
    
    # Запуск тестов
    tests_passed, total_tests = run_basic_tests()
    
    # Итоговый отчет
    print("\n📊 ИТОГОВЫЙ ОТЧЕТ:")
    print("=" * 50)
    
    passed_checks = sum(1 for _, result in results if result)
    total_checks = len(results)
    
    for name, result in results:
        status = "✅ ПРОЙДЕНА" if result else "❌ НЕ ПРОЙДЕНА"
        print(f"  {name:20} | {status}")
    
    print(f"\nТесты функций:      {tests_passed}/{total_tests} пройдено")
    print(f"Проверки окружения: {passed_checks}/{total_checks} пройдено")
    
    if passed_checks == total_checks and tests_passed == total_tests:
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Окружение готово к работе.")
        return True
    else:
        print("\n⚠️  ЕСТЬ ПРОБЛЕМЫ. Необходимо исправить ошибки.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
