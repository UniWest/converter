#!/usr/bin/env python
"""
Пример использования модели ConversionTask
Показывает, как работать с задачами конвертации
"""

import os
import sys
import django
import time

# Настройка Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
django.setup()

from converter.models import ConversionTask


def create_example_task():
    """Создать пример задачи конвертации"""
    task = ConversionTask.objects.create(
        task_metadata={
            'original_filename': 'example_video.mp4',
            'input_format': 'mp4',
            'output_format': 'avi',
            'file_size_mb': 125.7,
            'user_ip': '192.168.1.100',
            'conversion_settings': {
                'quality': 'high',
                'resolution': '1920x1080',
                'codec': 'h264'
            }
        }
    )
    
    print(f"Создана задача #{task.id}")
    print(f"Статус: {task.get_status_display()}")
    print(f"Прогресс: {task.progress}%")
    print(f"Метаданные: {task.task_metadata}")
    print(f"Создана: {task.created_at}")
    print("-" * 50)
    
    return task


def simulate_task_processing(task):
    """Симуляция обработки задачи"""
    print(f"Запуск задачи #{task.id}...")
    task.start()
    print(f"Статус: {task.get_status_display()}")
    
    # Симуляция прогресса выполнения
    for progress in [10, 30, 50, 75, 90]:
        time.sleep(1)  # Имитация работы
        task.update_progress(progress)
        print(f"Прогресс: {progress}%")
    
    # Завершение задачи
    task.complete()
    print(f"Задача завершена! Финальный статус: {task.get_status_display()}")
    print(f"Длительность выполнения: {task.duration}")
    print("-" * 50)


def create_failed_task():
    """Создать пример неудачной задачи"""
    task = ConversionTask.objects.create(
        task_metadata={
            'original_filename': 'corrupted_video.mkv',
            'input_format': 'mkv',
            'output_format': 'mp4',
            'file_size_mb': 89.2,
        }
    )
    
    print(f"Создана задача #{task.id}")
    task.start()
    task.update_progress(25)
    
    # Имитация ошибки
    task.fail("Ошибка: поврежденный исходный файл. Невозможно прочитать заголовок видео.")
    
    print(f"Задача #{task.id} завершилась с ошибкой")
    print(f"Сообщение об ошибке: {task.error_message}")
    print("-" * 50)
    
    return task


def show_all_tasks():
    """Показать все задачи в системе"""
    tasks = ConversionTask.objects.all()
    
    print(f"Всего задач в системе: {tasks.count()}")
    print("=" * 60)
    
    for task in tasks:
        print(f"Задача #{task.id}")
        print(f"  Статус: {task.get_status_display()}")
        print(f"  Прогресс: {task.progress}%")
        print(f"  Файл: {task.get_metadata('original_filename', 'Неизвестно')}")
        print(f"  Конвертация: {task.get_metadata('input_format', '?').upper()} → {task.get_metadata('output_format', '?').upper()}")
        print(f"  Создана: {task.created_at.strftime('%d.%m.%Y %H:%M:%S')}")
        if task.is_finished:
            print(f"  Завершена: {task.completed_at.strftime('%d.%m.%Y %H:%M:%S') if task.completed_at else 'N/A'}")
            if task.duration:
                print(f"  Длительность: {task.duration}")
        if task.error_message:
            print(f"  Ошибка: {task.error_message}")
        print("-" * 40)


def main():
    """Основная функция для демонстрации"""
    print("=== Демонстрация модели ConversionTask ===\n")
    
    # Создаем и обрабатываем успешную задачу
    print("1. Создание и обработка успешной задачи:")
    task1 = create_example_task()
    simulate_task_processing(task1)
    
    print("\n2. Создание неудачной задачи:")
    task2 = create_failed_task()
    
    print("\n3. Обзор всех задач:")
    show_all_tasks()
    
    print("\n4. Статистика по статусам:")
    for status_code, status_name in ConversionTask.STATUS_CHOICES:
        count = ConversionTask.objects.filter(status=status_code).count()
        print(f"  {status_name}: {count}")
    
    print("\n5. Активные задачи:")
    active_tasks = ConversionTask.objects.filter(
        status__in=[ConversionTask.STATUS_QUEUED, ConversionTask.STATUS_RUNNING]
    )
    print(f"  Количество активных задач: {active_tasks.count()}")
    
    print("\nДемонстрация завершена!")


if __name__ == "__main__":
    main()
