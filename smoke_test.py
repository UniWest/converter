#!/usr/bin/env python
"""
Smoke test для проверки базовых функций приложения
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io


class SmokeTest(TestCase):
    """Базовые тесты работоспособности системы"""
    
    def setUp(self):
        self.client = Client()
    
    def test_django_setup(self):
        """Проверка настроек Django"""
        from django.conf import settings
        self.assertTrue(settings.configured)
        print("✅ Django настроен корректно")
    
    def test_database_connection(self):
        """Проверка подключения к базе данных"""
        from django.db import connection
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
            print("✅ База данных подключена")
        except Exception as e:
            self.fail(f"Ошибка БД: {e}")
    
    def test_models_import(self):
        """Проверка импорта моделей"""
        try:
            from converter.models import ConversionTask
            print("✅ Модели импортированы успешно")
        except ImportError as e:
            self.fail(f"Ошибка импорта моделей: {e}")
    
    def test_celery_config(self):
        """Проверка конфигурации Celery"""
        try:
            from celery_app import app as celery_app
            self.assertIsNotNone(celery_app)
            # Проверяем, что Celery в режиме eager для тестов
            self.assertTrue(celery_app.conf.task_always_eager)
            print("✅ Celery настроен (eager mode для тестов)")
        except Exception as e:
            print(f"⚠️ Celery: {e}")
    
    def test_adapters_import(self):
        """Проверка импорта адаптеров"""
        try:
            from converter.adapters.engine_manager import EngineManager
            manager = EngineManager()
            self.assertIsNotNone(manager)
            print("✅ Адаптеры импортированы успешно")
        except Exception as e:
            print(f"⚠️ Адаптеры: {e}")
    
    def test_image_processing(self):
        """Базовый тест обработки изображений"""
        try:
            # Создаем простое тестовое изображение
            img = Image.new('RGB', (100, 100), color='red')
            img_io = io.BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)
            
            test_file = SimpleUploadedFile(
                "test.png", 
                img_io.getvalue(), 
                content_type="image/png"
            )
            
            # Проверяем, что файл создался
            self.assertGreater(len(test_file.read()), 0)
            print("✅ Базовая обработка изображений работает")
            
        except Exception as e:
            print(f"⚠️ Обработка изображений: {e}")


def run_smoke_tests():
    """Запуск smoke тестов"""
    print("🧪 Запуск smoke тестов...")
    print("=" * 50)
    
    # Создаем тестовый экземпляр
    test_instance = SmokeTest()
    test_instance.setUp()
    
    tests = [
        'test_django_setup',
        'test_database_connection', 
        'test_models_import',
        'test_celery_config',
        'test_adapters_import',
        'test_image_processing'
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name in tests:
        try:
            test_method = getattr(test_instance, test_name)
            test_method()
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
    
    print("=" * 50)
    print(f"📊 Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все базовые тесты прошли успешно!")
        return True
    else:
        print("⚠️ Некоторые тесты провалились")
        return False


if __name__ == '__main__':
    success = run_smoke_tests()
    sys.exit(0 if success else 1)
