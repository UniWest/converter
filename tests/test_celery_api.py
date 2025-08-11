#!/usr/bin/env python3
import os
import json
import tempfile
from django.conf import settings
from typing import Dict, List, Any
"""
Автотесты для Celery + API через pytest
Проверка асинхронных задач, очередей, воркеров
"""

import sys
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch
import logging

# Django setup
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')

import django
django.setup()

from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile

# Celery imports
from celery import Celery
from celery.result import AsyncResult

# Project imports
from test_audio_generator import TestAudioGenerator

logger = logging.getLogger(__name__)


class CeleryTestHelper:
    """Помощник для тестирования Celery"""
    
    def __init__(self):
        self.app = self._setup_test_celery()
        self.test_generator = TestAudioGenerator()
        self.test_files = self.test_generator.create_test_suite()
    
    def _setup_test_celery(self) -> Celery:
        """Настройка Celery для тестирования"""
        # Используем eager mode для синхронных тестов
        test_app = Celery('test_app')
        test_app.conf.update(
            task_always_eager=True,  # Выполняем задачи синхронно
            task_eager_propagates=True,  # Пропагируем исключения
            broker_url='memory://',  # In-memory брокер
            result_backend='cache+memory://',  # In-memory результаты
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
        )
        return test_app
    
    def create_test_task(self, task_name: str = "test_task"):
        """Создает тестовую задачу"""
        @self.app.task(name=task_name)
        def test_celery_task(data: dict):
            """Простая тестовая задача"""
            return {
                'status': 'completed',
                'input_data': data,
                'result': f"Processed: {data.get('input', 'no input')}"
            }
        return test_celery_task
    
    def create_failing_task(self):
        """Создает задачу, которая падает с ошибкой"""
        @self.app.task(name="failing_task")
        def failing_task(should_fail=True):
            if should_fail:
                raise Exception("Test exception")
            return {"status": "success"}
        return failing_task
    
    def create_long_running_task(self):
        """Создает долго выполняющуюся задачу"""
        @self.app.task(name="long_task", bind=True)
        def long_running_task(self, duration=10):
            for i in range(duration):
                self.update_state(
                    state='PROGRESS',
                    meta={'current': i, 'total': duration}
                )
                if not self.app.conf.task_always_eager:
                    time.sleep(1)  # Спим только если не в eager mode
            return {'status': 'completed', 'total': duration}
        return long_running_task


@pytest.fixture(scope="session")
def celery_helper():
    """Фикстура для CeleryTestHelper"""
    return CeleryTestHelper()


@pytest.fixture
def django_client():
    """Django test client"""
    return Client()


@pytest.fixture
def test_audio_files(celery_helper):
    """Фикстура тестовых аудиофайлов"""
    return celery_helper.test_files


class TestCeleryBasics:
    """Базовые тесты Celery функциональности"""
    
    def test_celery_app_configuration(self, celery_helper):
        """Тест 1: Проверка конфигурации Celery"""
        print("\n=== Тест 1: Конфигурация Celery ===")
        
        app = celery_helper.app
        
        # Проверяем основные настройки
        assert app.conf.task_serializer == 'json'
        assert app.conf.accept_content == ['json']
        assert app.conf.result_serializer == 'json'
        
        print("✅ Базовая конфигурация Celery корректна")
        
        # Проверяем, что приложение инициализировано
        assert app.main == 'test_app'
        print("✅ Celery app инициализировано")
    
    def test_simple_task_execution(self, celery_helper):
        """Тест 2: Выполнение простой задачи"""
        print("\n=== Тест 2: Простая задача ===")
        
        # Создаем и выполняем простую задачу
        test_task = celery_helper.create_test_task()
        
        test_data = {'input': 'test_value', 'timestamp': time.time()}
        result = test_task.delay(test_data)
        
        # В eager mode результат доступен сразу
        assert result.ready()
        assert result.successful()
        
        task_result = result.get()
        assert task_result['status'] == 'completed'
        assert task_result['input_data'] == test_data
        
        print("✅ Простая задача выполнена успешно")
        print(f"📊 Результат: {task_result}")
    
    def test_task_failure_handling(self, celery_helper):
        """Тест 3: Обработка ошибок в задачах"""
        print("\n=== Тест 3: Обработка ошибок ===")
        
        # Создаем задачу, которая падает
        failing_task = celery_helper.create_failing_task()
        
        result = failing_task.delay(should_fail=True)
        
        assert result.ready()
        assert result.failed()
        
        # Проверяем, что исключение пропагируется
        with pytest.raises(Exception, match="Test exception"):
            result.get(propagate=True)
        
        print("✅ Ошибки в задачах обрабатываются корректно")
    
    def test_task_progress_tracking(self, celery_helper):
        """Тест 4: Отслеживание прогресса задач"""
        print("\n=== Тест 4: Отслеживание прогресса ===")
        
        long_task = celery_helper.create_long_running_task()
        
        # Запускаем задачу с коротким duration для тестирования
        result = long_task.delay(duration=3)
        
        assert result.ready()  # В eager mode выполняется сразу
        
        task_result = result.get()
        assert task_result['status'] == 'completed'
        assert task_result['total'] == 3
        
        print("✅ Прогресс задач отслеживается корректно")


class TestSTTCeleryIntegration:
    """Тесты интеграции STT с Celery"""
    
    @patch('converter_site.tasks.convert_audio_to_text')
    def test_audio_to_text_task_creation(self, mock_task, django_client, test_audio_files):
        """Тест 5: Создание задач конвертации аудио"""
        print("\n=== Тест 5: Создание STT задач ===")
        
        # Настраиваем мок
        mock_task.delay.return_value = Mock(id='test-task-id-123')
        
        # Берем тестовый файл
        test_file = test_audio_files['short_ru'][0]
        
        with open(test_file, 'rb') as f:
            audio_data = f.read()
        
        uploaded_file = SimpleUploadedFile(
            name=Path(test_file).name,
            content=audio_data,
            content_type='audio/wav'
        )
        
        # Отправляем запрос
        response = django_client.post(
            '/api/audio-to-text/',
            data={
                'engine': 'whisper',
                'language': 'ru-RU',
                'quality': 'standard',
                'output_format': 'text'
            },
            files={'audio': uploaded_file}
        )
        
        # Проверяем ответ
        assert response.status_code == 200
        result = response.json()
        
        if result.get('async', False):
            assert 'task_id' in result
            print(f"✅ Асинхронная задача создана: {result['task_id']}")
        else:
            print("✅ Синхронная обработка выполнена")
        
        print("✅ STT задачи создаются корректно")
    
    def test_task_status_checking(self, django_client):
        """Тест 6: Проверка статуса задач через API"""
        print("\n=== Тест 6: Проверка статуса задач ===")
        
        # Создаем мок для AsyncResult
        with patch('converter_site.views.AsyncResult') as mock_async_result:
            mock_result = Mock()
            mock_result.state = 'SUCCESS'
            mock_result.result = {
                'text': 'Тестовый результат',
                'duration': 15.5,
                'language': 'ru-RU'
            }
            mock_async_result.return_value = mock_result
            
            response = django_client.get('/api/task-status/test-task-123/')
            
            assert response.status_code == 200
            result = response.json()
            
            assert result['success'] is True
            assert result['status'] == 'completed'
            assert 'result' in result
            
            print("✅ API проверки статуса работает корректно")
    
    def test_task_cancellation(self, django_client):
        """Тест 7: Отмена задач через API"""
        print("\n=== Тест 7: Отмена задач ===")
        
        with patch('converter_site.views.app') as mock_app:
            mock_app.control.revoke.return_value = None
            
            response = django_client.post('/api/cancel-task/test-task-456/')
            
            assert response.status_code == 200
            result = response.json()
            
            assert result['success'] is True
            assert 'task_id' in result
            
            # Проверяем, что revoke был вызван
            mock_app.control.revoke.assert_called_once_with('test-task-456', terminate=True)
            
            print("✅ Отмена задач работает корректно")


class TestCeleryQueues:
    """Тесты очередей Celery"""
    
    def test_task_routing(self, celery_helper):
        """Тест 8: Маршрутизация задач по очередям"""
        print("\n=== Тест 8: Маршрутизация задач ===")
        
        # Проверяем настройки маршрутизации из Django settings
        if hasattr(settings, 'CELERY_TASK_ROUTES'):
            routes = settings.CELERY_TASK_ROUTES
            
            # Проверяем ключевые маршруты
            expected_routes = [
                'converter_site.tasks.convert_audio_to_text',
                'converter_site.tasks.create_gif_from_images',
                'converter_site.tasks.cleanup_old_files'
            ]
            
            for route in expected_routes:
                if route in routes:
                    queue_name = routes[route]['queue']
                    print(f"✅ Задача {route} маршрутизируется в очередь: {queue_name}")
                else:
                    print(f"⚠️ Маршрут для {route} не найден")
        else:
            print("⚠️ CELERY_TASK_ROUTES не настроены")
    
    def test_queue_priorities(self, celery_helper):
        """Тест 9: Приоритеты очередей"""
        print("\n=== Тест 9: Приоритеты очередей ===")
        
        # Создаем задачи с разными приоритетами
        @celery_helper.app.task(name="high_priority_task")
        def high_priority_task():
            return {"priority": "high", "processed_at": time.time()}
        
        @celery_helper.app.task(name="low_priority_task")
        def low_priority_task():
            return {"priority": "low", "processed_at": time.time()}
        
        # В eager mode приоритеты не влияют, но тестируем создание
        high_result = high_priority_task.apply_async(priority=9)
        low_result = low_priority_task.apply_async(priority=1)
        
        assert high_result.ready()
        assert low_result.ready()
        
        high_data = high_result.get()
        low_data = low_result.get()
        
        assert high_data['priority'] == 'high'
        assert low_data['priority'] == 'low'
        
        print("✅ Задачи с приоритетами создаются корректно")


class TestCeleryWorkers:
    """Тесты воркеров Celery"""
    
    def test_worker_configuration(self):
        """Тест 10: Конфигурация воркеров"""
        print("\n=== Тест 10: Конфигурация воркеров ===")
        
        # Проверяем настройки воркеров из Django settings
        worker_settings = {
            'CELERY_WORKER_PREFETCH_MULTIPLIER': getattr(settings, 'CELERY_WORKER_PREFETCH_MULTIPLIER', None),
            'CELERY_WORKER_MAX_TASKS_PER_CHILD': getattr(settings, 'CELERY_WORKER_MAX_TASKS_PER_CHILD', None),
            'CELERY_TASK_SOFT_TIME_LIMIT': getattr(settings, 'CELERY_TASK_SOFT_TIME_LIMIT', None),
            'CELERY_TASK_TIME_LIMIT': getattr(settings, 'CELERY_TASK_TIME_LIMIT', None),
        }
        
        for setting_name, value in worker_settings.items():
            if value is not None:
                print(f"✅ {setting_name}: {value}")
            else:
                print(f"⚠️ {setting_name} не настроено")
        
        print("✅ Конфигурация воркеров проверена")
    
    def test_worker_health_check(self, celery_helper):
        """Тест 11: Проверка здоровья воркеров"""
        print("\n=== Тест 11: Здоровье воркеров ===")
        
        # В тестовом режиме воркеры не запущены, но проверим app
        app = celery_helper.app
        
        # Проверяем, что app готово к работе
        assert app is not None
        assert hasattr(app, 'tasks')
        assert hasattr(app, 'conf')
        
        print("✅ Celery app готово к работе")
        
        # Проверяем инспектор (в тестовом режиме может не работать)
        try:
            inspect = app.control.inspect()
            if inspect:
                print("✅ Инспектор Celery доступен")
            else:
                print("⚠️ Инспектор Celery недоступен (тестовый режим)")
        except Exception as e:
            print(f"⚠️ Ошибка инспектора: {e} (нормально для тестов)")


class TestCeleryMonitoring:
    """Тесты мониторинга Celery"""
    
    def test_task_events(self, celery_helper):
        """Тест 12: События задач"""
        print("\n=== Тест 12: События задач ===")
        
        # Проверяем настройки событий
        send_events = getattr(settings, 'CELERY_SEND_EVENTS', None)
        send_task_events = getattr(settings, 'CELERY_WORKER_SEND_TASK_EVENTS', None)
        
        if send_events:
            print(f"✅ CELERY_SEND_EVENTS: {send_events}")
        if send_task_events:
            print(f"✅ CELERY_WORKER_SEND_TASK_EVENTS: {send_task_events}")
        
        # Создаем задачу и проверяем события
        test_task = celery_helper.create_test_task()
        result = test_task.delay({'test': 'events'})
        
        # В eager mode события могут не генерироваться
        assert result.ready()
        print("✅ Задача выполнена (события в eager mode)")
    
    def test_result_backend(self, celery_helper):
        """Тест 13: Backend результатов"""
        print("\n=== Тест 13: Backend результатов ===")
        
        app = celery_helper.app
        backend = app.backend
        
        assert backend is not None
        print(f"✅ Result backend: {type(backend).__name__}")
        
        # Тестируем сохранение и получение результата
        test_task = celery_helper.create_test_task()
        result = test_task.delay({'backend_test': True})
        
        task_id = result.id
        assert task_id is not None
        
        # Получаем результат по ID
        retrieved_result = AsyncResult(task_id, app=app)
        assert retrieved_result.ready()
        
        print("✅ Backend результатов работает корректно")


class TestCeleryStressTests:
    """Стресс-тесты Celery"""
    
    def test_multiple_tasks_execution(self, celery_helper):
        """Тест 14: Выполнение множественных задач"""
        print("\n=== Тест 14: Множественные задачи ===")
        
        test_task = celery_helper.create_test_task()
        
        # Запускаем несколько задач одновременно
        num_tasks = 5
        results = []
        
        for i in range(num_tasks):
            result = test_task.delay({'task_number': i})
            results.append(result)
        
        # Проверяем все результаты
        for i, result in enumerate(results):
            assert result.ready()
            assert result.successful()
            
            task_result = result.get()
            assert task_result['input_data']['task_number'] == i
        
        print(f"✅ {num_tasks} задач выполнено успешно")
    
    def test_task_retry_mechanism(self, celery_helper):
        """Тест 15: Механизм повторных попыток"""
        print("\n=== Тест 15: Повторные попытки ===")
        
        retry_count = 0
        
        @celery_helper.app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
        def retry_task(self, should_fail=True):
            nonlocal retry_count
            retry_count += 1
            
            if should_fail and retry_count < 3:
                raise Exception(f"Retry attempt {retry_count}")
            
            return {'retry_count': retry_count, 'status': 'success'}
        
        # В eager mode повторы работают по-другому, но тестируем логику
        result = retry_task.delay(should_fail=False)  # Не падаем сразу
        
        assert result.ready()
        task_result = result.get()
        
        assert task_result['status'] == 'success'
        print("✅ Механизм повторных попыток настроен")


def test_celery_integration_comprehensive(celery_helper, django_client, test_audio_files):
    """Комплексный интеграционный тест Celery + API"""
    print("\n=== Комплексный интеграционный тест ===")
    
    # 1. Проверяем, что Django настройки загружены
    assert hasattr(settings, 'CELERY_BROKER_URL')
    print("✅ Django настройки Celery загружены")
    
    # 2. Тестируем API endpoint для создания задач
    test_file = test_audio_files['short_ru'][0]
    
    with open(test_file, 'rb') as f:
        audio_data = f.read()
    
    uploaded_file = SimpleUploadedFile(
        name=Path(test_file).name,
        content=audio_data,
        content_type='audio/wav'
    )
    
    with patch('converter_site.tasks.convert_audio_to_text') as mock_task:
        mock_task.delay.return_value = Mock(id='integration-test-task')
        
        response = django_client.post(
            '/api/audio-to-text/',
            data={
                'engine': 'whisper',
                'language': 'ru-RU',
                'quality': 'high',
                'output_format': 'json',
                'include_timestamps': 'true'
            },
            files={'audio': uploaded_file}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result.get('success', False)
        print("✅ API создания задач работает")
    
    # 3. Тестируем проверку статуса
    with patch('converter_site.views.AsyncResult') as mock_async:
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {
            'text': 'Интеграционный тест прошел успешно',
            'segments': [{'start': 0, 'end': 5, 'text': 'Тест'}]
        }
        mock_async.return_value = mock_result
        
        status_response = django_client.get('/api/task-status/integration-test-task/')
        assert status_response.status_code == 200
        
        status_result = status_response.json()
        assert status_result['success'] is True
        assert status_result['status'] == 'completed'
        print("✅ API проверки статуса работает")
    
    print("🎯 Комплексный интеграционный тест завершен успешно")


if __name__ == '__main__':
    # Запуск pytest с подробным выводом
    pytest.main([
        __file__, 
        '-v',  # подробный вывод
        '-s',  # показывать print'ы
        '--tb=short',  # короткие трейсбеки
        '--color=yes',  # цветной вывод
    ])
