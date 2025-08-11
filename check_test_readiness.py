#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт проверки готовности к тестированию STT системы
Шаг 8: Тестирование функциональности

Проверяет наличие всех компонентов для комплексного тестирования:
1. Тестовые файлы и скрипты
2. Зависимости Python 
3. Настройки Django
4. Конфигурация Celery
5. Структура проекта
"""

import os
import sys
import importlib
import subprocess
from datetime import datetime

class TestReadinessChecker:
    def __init__(self):
        self.checks_passed = 0
        self.checks_total = 0
        self.issues = []
        self.recommendations = []
        
    def check(self, description, condition, fix_suggestion=None):
        """Выполняет проверку и записывает результат"""
        self.checks_total += 1
        print(f"  {'✅' if condition else '❌'} {description}")
        
        if condition:
            self.checks_passed += 1
        else:
            self.issues.append(description)
            if fix_suggestion:
                self.recommendations.append(fix_suggestion)
    
    def print_header(self, title):
        """Печать заголовка секции"""
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print('='*60)
    
    def check_test_files(self):
        """Проверка наличия тестовых файлов"""
        self.print_header("ПРОВЕРКА ТЕСТОВЫХ ФАЙЛОВ")
        
        test_files = {
            "tests/test_audio_generator.py": "Генератор тестовых аудиофайлов",
            "tests/test_stt_functionality.py": "Тесты API функциональности STT",
            "tests/test_ui_functionality.py": "Тесты пользовательского интерфейса",
            "tests/test_celery_api.py": "Тесты Celery + API",
            "tests/run_all_tests.py": "Главный скрипт запуска тестов",
            "tests/requirements_tests.txt": "Зависимости для тестов",
            "tests/README.md": "Документация по тестированию",
            "demo_testing.py": "Демонстрационный скрипт"
        }
        
        for file_path, description in test_files.items():
            exists = os.path.exists(file_path)
            self.check(
                f"{description} ({file_path})",
                exists,
                f"Создайте файл {file_path}" if not exists else None
            )
    
    def check_python_dependencies(self):
        """Проверка Python зависимостей"""
        self.print_header("ПРОВЕРКА PYTHON ЗАВИСИМОСТЕЙ")
        
        required_packages = {
            "django": "Веб-фреймворк Django",
            "pytest": "Фреймворк для тестирования",
            "celery": "Асинхронная обработка задач", 
            "redis": "База данных Redis для Celery",
            "requests": "HTTP клиент для API тестов"
        }
        
        optional_packages = {
            "selenium": "Автоматизация браузера для UI тестов",
            "pydub": "Обработка аудиофайлов",
            "pytest-django": "Интеграция pytest с Django",
            "coverage": "Измерение покрытия кода"
        }
        
        # Проверка обязательных пакетов
        for package, description in required_packages.items():
            try:
                importlib.import_module(package)
                self.check(f"{description} ({package})", True)
            except ImportError:
                self.check(
                    f"{description} ({package})",
                    False,
                    f"Установите: pip install {package}"
                )
        
        # Проверка опциональных пакетов
        print("\n  📋 Опциональные зависимости:")
        for package, description in optional_packages.items():
            try:
                importlib.import_module(package)
                print(f"    ✅ {description} ({package})")
            except ImportError:
                print(f"    ⚠️ {description} ({package}) - не установлен")
    
    def check_django_config(self):
        """Проверка конфигурации Django"""
        self.print_header("ПРОВЕРКА КОНФИГУРАЦИИ DJANGO")
        
        django_files = {
            "manage.py": "Скрипт управления Django",
            "converter_site/settings.py": "Настройки Django",
            "converter_site/urls.py": "URL маршруты",
            "converter/models.py": "Модели данных",
            "converter/views.py": "Представления (views)",
            "converter/tasks.py": "Celery задачи"
        }
        
        for file_path, description in django_files.items():
            exists = os.path.exists(file_path)
            self.check(f"{description} ({file_path})", exists)
        
        # Проверка переменных окружения Django
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        self.check(
            "Переменная DJANGO_SETTINGS_MODULE установлена",
            django_settings is not None,
            "Установите: set DJANGO_SETTINGS_MODULE=converter_site.settings"
        )
    
    def check_celery_config(self):
        """Проверка конфигурации Celery"""
        self.print_header("ПРОВЕРКА КОНФИГУРАЦИИ CELERY")
        
        # Проверка файлов Celery
        celery_files = {
            "converter_site/celery.py": "Конфигурация Celery",
            "converter/tasks.py": "Определения задач Celery"
        }
        
        for file_path, description in celery_files.items():
            exists = os.path.exists(file_path)
            self.check(f"{description} ({file_path})", exists)
        
        # Проверка доступности Redis (простая проверка порта)
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 6379))
            sock.close()
            redis_available = result == 0
        except:
            redis_available = False
            
        self.check(
            "Redis сервер доступен на порту 6379",
            redis_available,
            "Запустите Redis: redis-server или docker run -d -p 6379:6379 redis"
        )
    
    def check_project_structure(self):
        """Проверка структуры проекта"""
        self.print_header("ПРОВЕРКА СТРУКТУРЫ ПРОЕКТА")
        
        directories = [
            "converter/",
            "converter_site/", 
            "tests/",
            "media/",
            "static/"
        ]
        
        for directory in directories:
            exists = os.path.isdir(directory)
            self.check(
                f"Директория {directory}",
                exists,
                f"Создайте директорию: mkdir {directory}" if not exists else None
            )
        
        # Проверка важных файлов проекта
        important_files = [
            "requirements.txt",
            "db.sqlite3"  # или другая база данных
        ]
        
        for file_path in important_files:
            exists = os.path.exists(file_path)
            self.check(f"Файл {file_path}", exists)
    
    def check_system_requirements(self):
        """Проверка системных требований"""
        self.print_header("ПРОВЕРКА СИСТЕМНЫХ ТРЕБОВАНИЙ")
        
        # Проверка версии Python
        python_version = sys.version_info
        python_ok = python_version >= (3, 8)
        self.check(
            f"Python версия >= 3.8 (текущая: {python_version.major}.{python_version.minor})",
            python_ok,
            "Обновите Python до версии 3.8 или выше"
        )
        
        # Проверка доступного места на диске (приблизительно)
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            free_gb = free // (1024**3)
            space_ok = free_gb >= 1  # минимум 1 ГБ
            self.check(
                f"Свободное место на диске >= 1 ГБ (доступно: {free_gb} ГБ)",
                space_ok,
                "Освободите место на диске"
            )
        except:
            self.check("Проверка места на диске", False, "Не удалось проверить место на диске")
    
    def generate_report(self):
        """Генерация итогового отчета"""
        self.print_header("ИТОГОВЫЙ ОТЧЕТ ГОТОВНОСТИ")
        
        success_rate = (self.checks_passed / self.checks_total) * 100
        
        print(f"📊 Всего проверок: {self.checks_total}")
        print(f"✅ Успешных: {self.checks_passed}")
        print(f"❌ Неудачных: {self.checks_total - self.checks_passed}")
        print(f"🎯 Готовность к тестированию: {success_rate:.1f}%")
        
        if success_rate >= 90:
            status = "✅ ГОТОВ К ТЕСТИРОВАНИЮ"
            print(f"\n{status}")
            print("   Система полностью готова для запуска тестов")
        elif success_rate >= 75:
            status = "⚠️ ПОЧТИ ГОТОВ"
            print(f"\n{status}")
            print("   Рекомендуется устранить оставшиеся проблемы перед тестированием")
        else:
            status = "❌ НЕ ГОТОВ"
            print(f"\n{status}")
            print("   Необходимо устранить критические проблемы")
        
        if self.issues:
            print(f"\n🔧 Обнаруженные проблемы:")
            for issue in self.issues:
                print(f"   • {issue}")
        
        if self.recommendations:
            print(f"\n💡 Рекомендации по устранению:")
            for recommendation in self.recommendations:
                print(f"   • {recommendation}")
        
        print(f"\n🚀 Следующие шаги:")
        if success_rate >= 75:
            print("   1. Установите недостающие зависимости")
            print("   2. Запустите demo_testing.py для демонстрации")  
            print("   3. Запустите tests/run_all_tests.py для полного тестирования")
        else:
            print("   1. Устраните критические проблемы из списка выше")
            print("   2. Перезапустите проверку готовности")
            print("   3. Установите требуемые зависимости")
        
        return success_rate >= 75
    
    def run_all_checks(self):
        """Запуск всех проверок"""
        print("🔍 ПРОВЕРКА ГОТОВНОСТИ К ТЕСТИРОВАНИЮ STT СИСТЕМЫ")
        print(f"📅 Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.check_test_files()
        self.check_python_dependencies()
        self.check_django_config()
        self.check_celery_config() 
        self.check_project_structure()
        self.check_system_requirements()
        
        return self.generate_report()

def main():
    """Главная функция"""
    checker = TestReadinessChecker()
    
    try:
        is_ready = checker.run_all_checks()
        sys.exit(0 if is_ready else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Проверка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка при проверке готовности: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
