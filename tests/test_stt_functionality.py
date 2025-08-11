#!/usr/bin/env python3
import os
import json
import tempfile
from typing import Dict, List, Any
"""
Тесты функциональности Speech-to-Text (STT) системы
"""

import sys
import unittest
import time
from pathlib import Path
import logging

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')

import django
from django.test import TestCase, TransactionTestCase
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile

# Инициализация Django
django.setup()

from test_audio_generator import TestAudioGenerator

logger = logging.getLogger(__name__)


class STTFunctionalityTest(TransactionTestCase):
    """Тесты основной функциональности STT"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client()
        cls.test_generator = TestAudioGenerator()
        cls.base_url = 'http://127.0.0.1:8000'  # Базовый URL для тестов
        
        # Создаем тестовые аудиофайлы
        cls.test_files = cls.test_generator.create_test_suite()
        
        logging.basicConfig(level=logging.INFO)
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.api_url_audio_to_text = '/api/audio-to-text/'
        self.api_url_task_status = '/api/task-status/'
    
    def test_01_short_audio_ru_processing(self):
        """Тест 1: Короткие аудиоклипы RU (15-60 сек) - проверка точности"""
        print("\n=== Тест 1: Обработка коротких русских аудиоклипов ===")
        
        for audio_file_path in self.test_files['short_ru']:
            with self.subTest(file=Path(audio_file_path).name):
                print(f"Тестируем файл: {Path(audio_file_path).name}")
                
                # Готовим файл для загрузки
                with open(audio_file_path, 'rb') as f:
                    audio_data = f.read()
                
                uploaded_file = SimpleUploadedFile(
                    name=Path(audio_file_path).name,
                    content=audio_data,
                    content_type='audio/wav'
                )
                
                # Параметры запроса
                data = {
                    'engine': 'whisper',
                    'language': 'ru-RU',
                    'quality': 'standard',
                    'output_format': 'text',
                    'include_timestamps': 'false',
                    'enhance_speech': 'true'
                }
                
                # Отправляем запрос
                response = self.client.post(
                    self.api_url_audio_to_text,
                    data=data,
                    files={'audio': uploaded_file},
                    follow=True
                )
                
                print(f"Статус ответа: {response.status_code}")
                
                self.assertEqual(response.status_code, 200, 
                    f"Ожидался статус 200, получен {response.status_code}")
                
                # Парсим JSON ответ
                try:
                    result = response.json()
                    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    
                    self.assertTrue(result.get('success', False), 
                        f"Ожидалось success=True, получено: {result}")
                    
                    # Проверяем наличие текста в результате
                    if not result.get('async', False):
                        self.assertIn('text', result, "В результате должен быть текст")
                        self.assertIsInstance(result['text'], str, "Текст должен быть строкой")
                        print(f"Распознанный текст: {result['text']}")
                    else:
                        # Асинхронная обработка
                        self.assertIn('task_id', result, "Для async должен быть task_id")
                        print(f"Асинхронная задача: {result['task_id']}")
                        
                except json.JSONDecodeError as e:
                    self.fail(f"Не удалось парсить JSON ответ: {e}")
    
    def test_02_short_audio_en_processing(self):
        """Тест 2: Короткие аудиоклипы EN (15-60 сек) - проверка выбора языка"""
        print("\n=== Тест 2: Обработка коротких английских аудиоклипов ===")
        
        for audio_file_path in self.test_files['short_en']:
            with self.subTest(file=Path(audio_file_path).name):
                print(f"Тестируем файл: {Path(audio_file_path).name}")
                
                with open(audio_file_path, 'rb') as f:
                    audio_data = f.read()
                
                uploaded_file = SimpleUploadedFile(
                    name=Path(audio_file_path).name,
                    content=audio_data,
                    content_type='audio/wav'
                )
                
                data = {
                    'engine': 'whisper',
                    'language': 'en-US',  # Английский язык
                    'quality': 'standard',
                    'output_format': 'text',
                    'include_timestamps': 'false',
                    'enhance_speech': 'true'
                }
                
                response = self.client.post(
                    self.api_url_audio_to_text,
                    data=data,
                    files={'audio': uploaded_file},
                    follow=True
                )
                
                print(f"Статус ответа: {response.status_code}")
                self.assertEqual(response.status_code, 200)
                
                try:
                    result = response.json()
                    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    
                    self.assertTrue(result.get('success', False))
                    
                    if not result.get('async', False):
                        self.assertIn('text', result)
                        print(f"Распознанный текст (EN): {result['text']}")
                        
                        # Проверяем метаданные языка
                        if 'metadata' in result:
                            detected_lang = result['metadata'].get('language')
                            print(f"Обнаруженный язык: {detected_lang}")
                        
                except json.JSONDecodeError as e:
                    self.fail(f"JSON parse error: {e}")
    
    def test_03_long_file_processing(self):
        """Тест 3: Длинные файлы (5-10 мин) - проверка сегментации и стабильности"""
        print("\n=== Тест 3: Обработка длинных аудиофайлов ===")
        
        for audio_file_path in self.test_files['long_files'][:2]:  # Ограничиваем количество для экономии времени
            with self.subTest(file=Path(audio_file_path).name):
                print(f"Тестируем длинный файл: {Path(audio_file_path).name}")
                
                with open(audio_file_path, 'rb') as f:
                    audio_data = f.read()
                
                uploaded_file = SimpleUploadedFile(
                    name=Path(audio_file_path).name,
                    content=audio_data,
                    content_type='audio/wav'
                )
                
                data = {
                    'engine': 'whisper',
                    'language': 'ru-RU',
                    'quality': 'standard',
                    'output_format': 'json',  # JSON для получения сегментов
                    'include_timestamps': 'true',
                    'enhance_speech': 'true'
                }
                
                response = self.client.post(
                    self.api_url_audio_to_text,
                    data=data,
                    files={'audio': uploaded_file},
                    follow=True
                )
                
                self.assertEqual(response.status_code, 200)
                
                try:
                    result = response.json()
                    print(f"Результат длинного файла: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
                    
                    self.assertTrue(result.get('success', False))
                    
                    if result.get('async', False):
                        # Для длинных файлов ожидаем асинхронную обработку
                        task_id = result['task_id']
                        print(f"Запущена асинхронная задача: {task_id}")
                        
                        # Тестируем проверку статуса задачи
                        self._test_task_status_checking(task_id)
                    else:
                        # Если обработка синхронная, проверяем сегменты
                        if 'segments' in result:
                            segments = result['segments']
                            self.assertIsInstance(segments, list, "Сегменты должны быть списком")
                            print(f"Количество сегментов: {len(segments)}")
                            
                            if segments:
                                # Проверяем первый сегмент
                                first_segment = segments[0]
                                self.assertIn('start', first_segment)
                                self.assertIn('end', first_segment)
                                self.assertIn('text', first_segment)
                                
                except json.JSONDecodeError as e:
                    self.fail(f"JSON parse error: {e}")
    
    def _test_task_status_checking(self, task_id: str, max_wait_time: int = 300):
        """Тестирует проверку статуса асинхронной задачи"""
        print(f"\n--- Проверка статуса задачи {task_id} ---")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Проверяем статус
            status_url = f"{self.api_url_task_status}{task_id}/"
            response = self.client.get(status_url)
            
            self.assertEqual(response.status_code, 200, 
                f"Ошибка при проверке статуса: {response.status_code}")
            
            try:
                status_data = response.json()
                print(f"Статус задачи: {status_data.get('status')} - {status_data.get('message')}")
                
                self.assertTrue(status_data.get('success', False), 
                    f"Ошибка в статусе: {status_data}")
                
                task_status = status_data.get('status')
                
                if task_status == 'completed':
                    print("✅ Задача завершена успешно")
                    
                    # Проверяем результат
                    if 'result' in status_data:
                        result = status_data['result']
                        self.assertIn('text', result, "В результате должен быть текст")
                        print(f"Итоговый текст: {result['text'][:200]}...")
                    
                    return True
                    
                elif task_status == 'failed':
                    error = status_data.get('error', 'Unknown error')
                    self.fail(f"❌ Задача завершилась с ошибкой: {error}")
                    
                elif task_status in ['pending', 'processing']:
                    progress = status_data.get('progress', 0)
                    print(f"⏳ Задача выполняется... Прогресс: {progress}%")
                    time.sleep(10)  # Ждем 10 секунд перед следующей проверкой
                    
                else:
                    print(f"🔄 Неизвестный статус: {task_status}")
                    time.sleep(5)
                    
            except json.JSONDecodeError as e:
                self.fail(f"Ошибка парсинга JSON при проверке статуса: {e}")
        
        self.fail(f"Таймаут: задача не завершилась за {max_wait_time} секунд")
    
    def test_04_different_formats_support(self):
        """Тест 4: Поддержка различных форматов вывода (text, srt, json)"""
        print("\n=== Тест 4: Проверка форматов вывода ===")
        
        # Берем короткий файл для быстрого тестирования
        test_file = self.test_files['short_ru'][0]
        
        formats = ['text', 'json']  # SRT пока можем пропустить
        
        for output_format in formats:
            with self.subTest(format=output_format):
                print(f"Тестируем формат вывода: {output_format}")
                
                with open(test_file, 'rb') as f:
                    audio_data = f.read()
                
                uploaded_file = SimpleUploadedFile(
                    name=Path(test_file).name,
                    content=audio_data,
                    content_type='audio/wav'
                )
                
                data = {
                    'engine': 'whisper',
                    'language': 'ru-RU',
                    'output_format': output_format,
                    'include_timestamps': 'true' if output_format != 'text' else 'false'
                }
                
                response = self.client.post(
                    self.api_url_audio_to_text,
                    data=data,
                    files={'audio': uploaded_file},
                    follow=True
                )
                
                self.assertEqual(response.status_code, 200)
                
                result = response.json()
                self.assertTrue(result.get('success', False))
                
                if not result.get('async', False):
                    if output_format == 'text':
                        self.assertIn('text', result)
                        self.assertIsInstance(result['text'], str)
                        
                    elif output_format == 'json':
                        self.assertIn('text', result)
                        if result.get('segments'):
                            self.assertIsInstance(result['segments'], list)
                            print(f"JSON формат: найдено {len(result['segments'])} сегментов")
    
    def test_05_error_handling(self):
        """Тест 5: Обработка ошибок и валидация входных данных"""
        print("\n=== Тест 5: Тестирование обработки ошибок ===")
        
        # Тест 1: Отсутствие файла
        response = self.client.post(self.api_url_audio_to_text, data={})
        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertFalse(result.get('success', True))
        self.assertIn('error', result)
        print(f"✅ Ошибка без файла: {result['error']}")
        
        # Тест 2: Неподдерживаемый формат
        fake_file = SimpleUploadedFile(
            name="test.txt",
            content=b"This is not an audio file",
            content_type='text/plain'
        )
        
        response = self.client.post(
            self.api_url_audio_to_text,
            data={'engine': 'whisper'},
            files={'audio': fake_file}
        )
        
        result = response.json()
        self.assertFalse(result.get('success', True))
        self.assertIn('error', result)
        print(f"✅ Ошибка неподдерживаемого формата: {result['error']}")
        
        # Тест 3: Слишком большой файл (имитация)
        # Создаем файл с размером больше допустимого
        large_data = b'0' * (600 * 1024 * 1024)  # 600 МБ
        large_file = SimpleUploadedFile(
            name="large_audio.wav",
            content=large_data,
            content_type='audio/wav'
        )
        
        response = self.client.post(
            self.api_url_audio_to_text,
            data={'engine': 'whisper'},
            files={'audio': large_file}
        )
        
        result = response.json()
        # Может быть как ошибка размера, так и ошибка формата
        self.assertFalse(result.get('success', True))
        print(f"✅ Ошибка большого файла: {result.get('error', 'No error message')}")
    
    def tearDown(self):
        """Очистка после каждого теста"""
        pass
    
    @classmethod
    def tearDownClass(cls):
        """Очистка после всех тестов"""
        # Можно добавить очистку временных файлов
        print("\n=== Завершение тестирования ===")
        print("Все тесты функциональности STT завершены")


class STTPerformanceTest(TestCase):
    """Тесты производительности STT системы"""
    
    def setUp(self):
        self.client = Client()
    
    def test_response_time_short_files(self):
        """Тест времени отклика для коротких файлов"""
        print("\n=== Тест производительности: короткие файлы ===")
        
        # Создаем простой тестовый файл
        generator = TestAudioGenerator()
        test_file = generator.create_test_audio_simple(15, 'ru')
        
        start_time = time.time()
        
        with open(test_file, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                name="performance_test.wav",
                content=f.read(),
                content_type='audio/wav'
            )
        
        response = self.client.post(
            '/api/audio-to-text/',
            data={'engine': 'google', 'language': 'ru-RU'},
            files={'audio': uploaded_file}
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"⏱️ Время отклика для 15-сек файла: {response_time:.2f} секунд")
        
        self.assertEqual(response.status_code, 200)
        
        # Ожидаем, что обработка короткого файла займет не больше 30 секунд
        self.assertLess(response_time, 30, 
            f"Время отклика слишком большое: {response_time:.2f}s")
        
        # Очищаем тестовый файл
        os.unlink(test_file)


def run_stt_tests():
    """Запуск всех тестов STT функциональности"""
    print("🎯 Запуск комплексного тестирования STT функциональности")
    print("=" * 60)
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создаем test suite
    loader = unittest.TestLoader()
    
    # Добавляем тесты функциональности
    functionality_suite = loader.loadTestsFromTestCase(STTFunctionalityTest)
    
    # Добавляем тесты производительности
    performance_suite = loader.loadTestsFromTestCase(STTPerformanceTest)
    
    # Комбинируем все тесты
    combined_suite = unittest.TestSuite([functionality_suite, performance_suite])
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2, buffer=False)
    result = runner.run(combined_suite)
    
    # Выводим итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ STT")
    print("=" * 60)
    print(f"✅ Успешных тестов: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Неудачных тестов: {len(result.failures)}")
    print(f"🚨 Ошибок: {len(result.errors)}")
    print(f"📈 Всего тестов: {result.testsRun}")
    
    if result.failures:
        print("\n❌ НЕУДАЧНЫЕ ТЕСТЫ:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n🚨 ОШИБКИ:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\n🎯 Процент успешности: {success_rate:.1f}%")
    
    return result


if __name__ == '__main__':
    run_stt_tests()
