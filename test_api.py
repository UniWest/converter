#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API эндпоинтов управления задачами конвертации.

Использование:
python test_api.py [BASE_URL]

По умолчанию BASE_URL = http://127.0.0.1:8000
"""

import requests
import json
import time
import sys
import os

# Базовый URL API
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/tasks"

def test_create_task_with_url():
    """Тест создания задачи через URL"""
    print("=== Тест создания задачи через URL ===")
    
    # Пример URL с видео (можно заменить на реальный)
    test_data = {
        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_360x240_1mb.mp4",
        "format": "gif",
        "width": 320,
        "fps": 10,
        "start_time": 0,
        "end_time": 5,
        "quality": "medium"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/create/",
            headers={"Content-Type": "application/json"},
            data=json.dumps(test_data)
        )
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("success"):
            return result.get("task_id")
        else:
            print("Ошибка создания задачи")
            return None
            
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return None

def test_create_task_with_file():
    """Тест создания задачи с файлом (если файл существует)"""
    print("\n=== Тест создания задачи с файлом ===")
    
    # Проверяем наличие тестового файла
    test_file = "test_video.mp4"
    if not os.path.exists(test_file):
        print(f"Файл {test_file} не найден, пропускаем тест с файлом")
        return None
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'video/mp4')}
            data = {
                'format': 'gif',
                'width': '480',
                'fps': '15',
                'quality': 'medium'
            }
            
            response = requests.post(f"{API_URL}/create/", files=files, data=data)
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("success"):
            return result.get("task_id")
        else:
            print("Ошибка создания задачи")
            return None
            
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return None

def test_task_status(task_id):
    """Тест получения статуса задачи"""
    print(f"\n=== Тест статуса задачи {task_id} ===")
    
    try:
        response = requests.get(f"{API_URL}/{task_id}/status/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result.get("status")
        else:
            print(f"Ошибка: {response.text}")
            return None
            
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return None

def test_task_result(task_id):
    """Тест получения результата задачи"""
    print(f"\n=== Тест результата задачи {task_id} ===")
    
    try:
        response = requests.get(f"{API_URL}/{task_id}/result/")
        print(f"Status: {response.status_code}")
        
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        return result.get("success", False)
        
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return False

def test_task_download(task_id):
    """Тест скачивания результата задачи"""
    print(f"\n=== Тест скачивания задачи {task_id} ===")
    
    try:
        response = requests.get(f"{API_URL}/{task_id}/download/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            # Пытаемся определить имя файла из заголовков
            content_disposition = response.headers.get('Content-Disposition', '')
            filename = f"downloaded_task_{task_id}.gif"  # По умолчанию
            
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"Файл сохранен как: {filename}")
            print(f"Размер: {len(response.content)} байт")
            return True
        else:
            print(f"Ошибка: {response.text}")
            return False
            
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return False

def test_tasks_list():
    """Тест получения списка задач"""
    print("\n=== Тест списка задач ===")
    
    try:
        response = requests.get(f"{API_URL}/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Количество задач: {len(result.get('tasks', []))}")
            print(f"Пагинация: {result.get('pagination', {})}")
            return result.get('tasks', [])
        else:
            print(f"Ошибка: {response.text}")
            return []
            
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return []

def test_batch_download(task_ids):
    """Тест пакетного скачивания"""
    print(f"\n=== Тест пакетного скачивания {task_ids} ===")
    
    if not task_ids:
        print("Нет задач для скачивания")
        return False
    
    try:
        # Тест через GET параметры
        task_ids_str = ','.join(map(str, task_ids))
        response = requests.get(f"{API_URL}/batch-download/?task_ids={task_ids_str}")
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            filename = "batch_download.zip"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"ZIP архив сохранен как: {filename}")
            print(f"Размер: {len(response.content)} байт")
            
            # Проверяем заголовки
            total_tasks = response.headers.get('X-Total-Tasks', 'N/A')
            successful_tasks = response.headers.get('X-Successful-Tasks', 'N/A')
            files_count = response.headers.get('X-Files-Count', 'N/A')
            
            print(f"Всего задач: {total_tasks}")
            print(f"Успешных задач: {successful_tasks}")
            print(f"Файлов в архиве: {files_count}")
            
            return True
        else:
            print(f"Ошибка: {response.text}")
            return False
            
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return False

def wait_for_completion(task_id, max_wait_time=300, check_interval=5):
    """Ожидание завершения задачи"""
    print(f"\n=== Ожидание завершения задачи {task_id} ===")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = test_task_status(task_id)
        
        if status == "done":
            print("Задача завершена успешно!")
            return True
        elif status == "failed":
            print("Задача завершилась с ошибкой!")
            return False
        elif status in ["queued", "running"]:
            print(f"Задача в статусе: {status}, ожидаем...")
            time.sleep(check_interval)
        else:
            print(f"Неизвестный статус: {status}")
            return False
    
    print("Превышено время ожидания!")
    return False

def main():
    """Основная функция тестирования"""
    print(f"Тестирование API по адресу: {API_URL}")
    print("=" * 50)
    
    # 1. Получаем список задач
    all_tasks = test_tasks_list()
    
    # 2. Создаем задачу через URL (если возможно)
    task_id = test_create_task_with_url()
    
    if task_id:
        print(f"\nСоздана задача: {task_id}")
        
        # 3. Ожидаем завершения задачи (с коротким таймаутом для теста)
        if wait_for_completion(task_id, max_wait_time=60, check_interval=3):
            # 4. Получаем результат
            test_task_result(task_id)
            
            # 5. Скачиваем файл
            test_task_download(task_id)
            
            # 6. Тестируем пакетное скачивание
            completed_tasks = [task_id]
            test_batch_download(completed_tasks)
    
    # 7. Тест создания задачи с файлом (если файл есть)
    file_task_id = test_create_task_with_file()
    if file_task_id:
        print(f"\nСоздана задача с файлом: {file_task_id}")
    
    print("\n" + "=" * 50)
    print("Тестирование завершено")

if __name__ == "__main__":
    main()
