#!/usr/bin/env python
"""
Тестовый скрипт для проверки новых функций:
1. Команды управления cleanup_old_files
2. Расширенного endpoint /status

Этот скрипт демонстрирует работу обеих функций.
"""

import os
import django
from datetime import datetime, timedelta

# Настройка Django
if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
    django.setup()

from django.core.management import call_command
from django.test.client import Client
from converter.models import ConversionTask


def test_cleanup_command():
    """Тестирование команды cleanup_old_files"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ КОМАНДЫ CLEANUP_OLD_FILES")
    print("=" * 60)
    
    # Создаем несколько тестовых задач
    print("Создаем тестовые задачи...")
    
    # Создаем старую задачу (7 дней назад)
    old_task = ConversionTask.objects.create(
        status=ConversionTask.STATUS_DONE,
        progress=100,
        created_at=datetime.now() - timedelta(days=7, hours=1),
        task_metadata={
            'original_filename': 'old_video.mp4',
            'output_filename': 'old_video.gif',
            'conversion_settings': {'fps': 15, 'width': 480}
        }
    )
    
    # Создаем новую задачу (1 день назад)
    new_task = ConversionTask.objects.create(
        status=ConversionTask.STATUS_DONE,
        progress=100,
        created_at=datetime.now() - timedelta(days=1),
        task_metadata={
            'original_filename': 'new_video.mp4',
            'output_filename': 'new_video.gif',
            'conversion_settings': {'fps': 20, 'width': 720}
        }
    )
    
    # Создаем неудачную старую задачу
    failed_old_task = ConversionTask.objects.create(
        status=ConversionTask.STATUS_FAILED,
        error_message="Test error for cleanup",
        created_at=datetime.now() - timedelta(days=10),
        task_metadata={
            'original_filename': 'failed_video.mp4',
            'error': 'Conversion failed'
        }
    )
    
    print(f"Создано задач: {ConversionTask.objects.count()}")
    print(f"Старых задач (>7 дней): {ConversionTask.objects.filter(created_at__lt=datetime.now() - timedelta(days=7)).count()}")
    
    # Тест 1: Dry-run режим
    print("\n--- Тест 1: Dry-run режим ---")
    try:
        call_command('cleanup_old_files', '--days=7', '--dry-run', verbosity=2)
        print("✅ Dry-run режим работает корректно")
    except Exception as e:
        print(f"❌ Ошибка в dry-run режиме: {e}")
    
    # Тест 2: Очистка только неудачных задач
    print("\n--- Тест 2: Очистка неудачных задач ---")
    try:
        call_command('cleanup_old_files', '--days=7', '--failed-only', verbosity=2)
        remaining_failed = ConversionTask.objects.filter(
            status=ConversionTask.STATUS_FAILED,
            created_at__lt=datetime.now() - timedelta(days=7)
        ).count()
        print(f"✅ Неудачных старых задач осталось: {remaining_failed}")
    except Exception as e:
        print(f"❌ Ошибка при очистке неудачных задач: {e}")
    
    # Тест 3: Обычная очистка
    print("\n--- Тест 3: Обычная очистка старых задач ---")
    try:
        tasks_before = ConversionTask.objects.count()
        call_command('cleanup_old_files', '--days=5', verbosity=2)
        tasks_after = ConversionTask.objects.count()
        print(f"✅ Задач до очистки: {tasks_before}, после: {tasks_after}")
        print(f"   Удалено задач: {tasks_before - tasks_after}")
    except Exception as e:
        print(f"❌ Ошибка при обычной очистке: {e}")


def test_status_endpoint():
    """Тестирование расширенного endpoint /status"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ РАСШИРЕННОГО ENDPOINT /STATUS")
    print("=" * 60)
    
    client = Client()
    
    try:
        response = client.get('/status/')
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Endpoint /status доступен")
            
            # Проверяем основные секции
            expected_sections = [
                'timestamp', 'system', 'resources', 'engines', 
                'binaries', 'media_paths', 'statistics', 'storage', 
                'recommended_engine', 'status'
            ]
            
            print("\n--- Структура ответа ---")
            for section in expected_sections:
                if section in data:
                    print(f"✅ {section}: присутствует")
                else:
                    print(f"❌ {section}: отсутствует")
            
            # Детальная информация о системе
            if 'system' in data:
                print(f"\n--- Системная информация ---")
                system_info = data['system']
                print(f"Платформа: {system_info.get('platform', 'N/A')}")
                print(f"Python: {system_info.get('python_version', 'N/A')}")
                print(f"Архитектура: {system_info.get('architecture', 'N/A')}")
            
            # Информация о ресурсах
            if 'resources' in data:
                print(f"\n--- Ресурсы системы ---")
                resources = data['resources']
                print(f"CPU ядер: {resources.get('cpu_count', 'N/A')}")
                
                if 'memory_total' in resources:
                    memory_total_gb = resources['memory_total'] / (1024**3)
                    memory_avail_gb = resources['memory_available'] / (1024**3)
                    print(f"Память: {memory_avail_gb:.1f}GB доступно / {memory_total_gb:.1f}GB всего")
                
                if 'disk_usage' in resources:
                    disk = resources['disk_usage']
                    disk_free_gb = disk['free'] / (1024**3)
                    disk_total_gb = disk['total'] / (1024**3)
                    print(f"Диск: {disk_free_gb:.1f}GB свободно / {disk_total_gb:.1f}GB всего")
            
            # Информация о движках конвертации
            if 'engines' in data:
                print(f"\n--- Движки конвертации ---")
                for engine_name, engine_info in data['engines'].items():
                    status_icon = "✅" if engine_info.get('available', False) else "❌"
                    version = engine_info.get('version', 'неизвестно')
                    print(f"{status_icon} {engine_name}: {engine_info.get('status', 'неизвестно')} (v{version})")
            
            # Информация о дополнительных бинарниках
            if 'binaries' in data:
                print(f"\n--- Дополнительные инструменты ---")
                for binary_name, binary_info in data['binaries'].items():
                    status_icon = "✅" if binary_info.get('available', False) else "❌"
                    print(f"{status_icon} {binary_name}: {binary_info.get('status', 'неизвестно')}")
            
            # Статистика задач
            if 'statistics' in data and 'error' not in data['statistics']:
                print(f"\n--- Статистика задач ---")
                stats = data['statistics']
                print(f"Всего задач: {stats.get('total_tasks', 0)}")
                print(f"В очереди: {stats.get('queued_tasks', 0)}")
                print(f"Выполняется: {stats.get('running_tasks', 0)}")
                print(f"Завершено: {stats.get('completed_tasks', 0)}")
                print(f"Неудачно: {stats.get('failed_tasks', 0)}")
            
            # Информация о хранилище
            if 'storage' in data and 'error' not in data['storage']:
                print(f"\n--- Использование хранилища ---")
                storage = data['storage']
                for folder, size in storage.items():
                    if isinstance(size, (int, float)):
                        size_mb = size / (1024**2)
                        print(f"{folder}: {size_mb:.1f}MB")
            
            print(f"\n--- Рекомендации ---")
            print(f"Рекомендуемый движок: {data.get('recommended_engine', 'неизвестно')}")
            print(f"Общий статус системы: {data.get('status', 'неизвестно')}")
            
        else:
            print(f"❌ Ошибка HTTP {response.status_code}: {response.content.decode()}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании endpoint: {e}")


def create_demo_data():
    """Создание демонстрационных данных для тестирования"""
    print("\n" + "=" * 60)
    print("СОЗДАНИЕ ДЕМОНСТРАЦИОННЫХ ДАННЫХ")
    print("=" * 60)
    
    # Создаем несколько задач разных типов и возрастов
    demo_tasks = [
        # Свежие активные задачи
        {
            'status': ConversionTask.STATUS_QUEUED,
            'created_at': datetime.now() - timedelta(minutes=30),
            'metadata': {'filename': 'recent_video1.mp4', 'size': 1024*1024*50}
        },
        {
            'status': ConversionTask.STATUS_RUNNING,
            'progress': 45,
            'started_at': datetime.now() - timedelta(minutes=10),
            'created_at': datetime.now() - timedelta(hours=2),
            'metadata': {'filename': 'processing_video.mp4', 'size': 1024*1024*120}
        },
        
        # Недавно завершенные
        {
            'status': ConversionTask.STATUS_DONE,
            'progress': 100,
            'created_at': datetime.now() - timedelta(days=2),
            'completed_at': datetime.now() - timedelta(days=2, hours=-1),
            'metadata': {'filename': 'completed_recent.mp4', 'output': 'completed_recent.gif'}
        },
        
        # Старые завершенные (для очистки)
        {
            'status': ConversionTask.STATUS_DONE,
            'progress': 100,
            'created_at': datetime.now() - timedelta(days=30),
            'completed_at': datetime.now() - timedelta(days=30, hours=-2),
            'metadata': {'filename': 'old_completed.mp4', 'output': 'old_completed.gif'}
        },
        
        # Старые неудачные (для очистки)
        {
            'status': ConversionTask.STATUS_FAILED,
            'error_message': 'FFmpeg process failed',
            'created_at': datetime.now() - timedelta(days=15),
            'metadata': {'filename': 'failed_conversion.mp4', 'error_code': 1}
        },
    ]
    
    created_count = 0
    for task_data in demo_tasks:
        metadata = task_data.pop('metadata', {})
        task = ConversionTask.objects.create(task_metadata=metadata, **task_data)
        created_count += 1
        print(f"Создана задача #{task.id}: {task.get_status_display()} ({task_data.get('created_at', 'now').strftime('%Y-%m-%d %H:%M')})")
    
    print(f"\n✅ Создано {created_count} демонстрационных задач")
    print(f"Всего задач в системе: {ConversionTask.objects.count()}")


if __name__ == "__main__":
    print("ТЕСТИРОВАНИЕ НОВЫХ ФУНКЦИЙ СИСТЕМЫ КОНВЕРТАЦИИ")
    print("=" * 60)
    
    # Создаем демонстрационные данные
    create_demo_data()
    
    # Тестируем endpoint статуса
    test_status_endpoint()
    
    # Тестируем команду очистки
    test_cleanup_command()
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    
    # Финальная статистика
    print(f"Итоговое количество задач: {ConversionTask.objects.count()}")
    for status, label in ConversionTask.STATUS_CHOICES:
        count = ConversionTask.objects.filter(status=status).count()
        if count > 0:
            print(f"  {label}: {count}")
