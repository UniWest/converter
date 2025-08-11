#!/usr/bin/env python
"""
Утилиты для тестирования конвертера видео в GIF.
Включает в себя вспомогательные функции и классы для создания тестовых данных.

Использование:
from test_utils import create_test_video_file, VideoTestCase, run_performance_tests
"""

import os
import tempfile
import time
from io import BytesIO
from unittest.mock import Mock, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile, InMemoryUploadedFile
from django.test import TestCase


class VideoFileGenerator:
    """Генератор тестовых видеофайлов для различных сценариев тестирования"""
    
    @staticmethod
    def create_small_video_file(filename="test_small.mp4", size_kb=10):
        """
        Создает небольшой тестовый видеофайл.
        
        Args:
            filename: имя файла
            size_kb: размер файла в килобайтах
        
        Returns:
            SimpleUploadedFile: тестовый видеофайл
        """
        # Генерируем фиктивные данные видеофайла
        content = b'FAKE_MP4_HEADER' + b'X' * (size_kb * 1024 - 15)
        
        return SimpleUploadedFile(
            filename,
            content,
            content_type="video/mp4"
        )
    
    @staticmethod
    def create_large_video_file(filename="test_large.mp4", size_mb=100):
        """
        Создает большой тестовый видеофайл для тестирования лимитов.
        
        Args:
            filename: имя файла
            size_mb: размер файла в мегабайтах
        
        Returns:
            InMemoryUploadedFile: большой тестовый видеофайл
        """
        # Создаем большой файл в памяти
        content = BytesIO()
        content.write(b'FAKE_LARGE_MP4_HEADER')
        
        # Заполняем остальное пространство
        chunk_size = 1024 * 1024  # 1MB chunks
        for i in range(size_mb):
            chunk = b'X' * chunk_size
            content.write(chunk)
        
        content.seek(0)
        
        return InMemoryUploadedFile(
            file=content,
            field_name="video",
            name=filename,
            content_type="video/mp4",
            size=size_mb * 1024 * 1024,
            charset=None
        )
    
    @staticmethod
    def create_various_format_files():
        """
        Создает файлы различных форматов для тестирования валидации.
        
        Returns:
            dict: словарь с файлами разных форматов
        """
        formats = {
            'mp4': SimpleUploadedFile("test.mp4", b"FAKE_MP4_CONTENT", "video/mp4"),
            'avi': SimpleUploadedFile("test.avi", b"FAKE_AVI_CONTENT", "video/avi"),
            'mov': SimpleUploadedFile("test.mov", b"FAKE_MOV_CONTENT", "video/quicktime"),
            'mkv': SimpleUploadedFile("test.mkv", b"FAKE_MKV_CONTENT", "video/x-matroska"),
            'txt': SimpleUploadedFile("test.txt", b"NOT_A_VIDEO", "text/plain"),
            'jpg': SimpleUploadedFile("test.jpg", b"FAKE_IMAGE", "image/jpeg"),
        }
        return formats


class MockVideoConverter:
    """Мок-класс для VideoConverter с предустановленным поведением"""
    
    def __init__(self, should_succeed=True, conversion_time=0.1):
        self.should_succeed = should_succeed
        self.conversion_time = conversion_time
        self.conversion_calls = []
        self.info_calls = []
    
    def convert_video_to_gif(self, video_file, output_path, **kwargs):
        """Имитирует конвертацию видео в GIF"""
        # Записываем вызов для анализа
        self.conversion_calls.append({
            'video_file': video_file,
            'output_path': output_path,
            'kwargs': kwargs
        })
        
        # Имитируем время обработки
        time.sleep(self.conversion_time)
        
        if self.should_succeed:
            # Создаем фиктивный GIF файл
            with open(output_path, 'wb') as f:
                f.write(b'FAKE_GIF_DATA_' + b'X' * 1000)
            return True
        else:
            return False
    
    def get_video_info(self, video_file):
        """Имитирует получение информации о видео"""
        self.info_calls.append(video_file)
        
        if self.should_succeed:
            return {
                'duration': 120.0,
                'width': 1920,
                'height': 1080,
                'fps': 30.0,
                'codec': 'h264',
                'bitrate': 5000000
            }
        else:
            return {}
    
    def _check_ffmpeg(self, ffmpeg_path):
        """Имитирует проверку доступности FFmpeg"""
        return self.should_succeed


class VideoTestCase(TestCase):
    """Базовый класс для тестов видео конвертера с дополнительными утилитами"""
    
    def setUp(self):
        """Базовая настройка для всех тестов"""
        super().setUp()
        self.video_generator = VideoFileGenerator()
        self.temp_files = []
        self.temp_dirs = []
    
    def tearDown(self):
        """Очистка после тестов"""
        # Очищаем временные файлы
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except (PermissionError, OSError):
                    pass
        
        # Очищаем временные директории
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except (PermissionError, OSError):
                    pass
        
        super().tearDown()
    
    def create_temp_file(self, suffix='.tmp', content=b'test'):
        """
        Создает временный файл и добавляет его в список для очистки.
        
        Args:
            suffix: расширение файла
            content: содержимое файла
        
        Returns:
            str: путь к временному файлу
        """
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        self.temp_files.append(temp_path)
        return temp_path
    
    def create_temp_dir(self, prefix='test_'):
        """
        Создает временную директорию и добавляет её в список для очистки.
        
        Args:
            prefix: префикс имени директории
        
        Returns:
            str: путь к временной директории
        """
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def assert_file_exists_and_not_empty(self, file_path):
        """
        Проверяет, что файл существует и не пустой.
        
        Args:
            file_path: путь к файлу
        """
        self.assertTrue(os.path.exists(file_path), f"Файл {file_path} не существует")
        
        file_size = os.path.getsize(file_path)
        self.assertGreater(file_size, 0, f"Файл {file_path} пустой")
    
    def assert_video_conversion_params(self, mock_converter, expected_width=None, 
                                     expected_fps=None, expected_start_time=None, 
                                     expected_end_time=None):
        """
        Проверяет параметры вызова конвертации видео.
        
        Args:
            mock_converter: мок объект конвертера
            expected_width: ожидаемая ширина
            expected_fps: ожидаемая частота кадров
            expected_start_time: ожидаемое время начала
            expected_end_time: ожидаемое время окончания
        """
        self.assertTrue(hasattr(mock_converter, 'conversion_calls'))
        self.assertGreater(len(mock_converter.conversion_calls), 0)
        
        last_call = mock_converter.conversion_calls[-1]
        kwargs = last_call['kwargs']
        
        if expected_width is not None:
            self.assertEqual(kwargs.get('width'), expected_width)
        
        if expected_fps is not None:
            self.assertEqual(kwargs.get('fps'), expected_fps)
        
        if expected_start_time is not None:
            self.assertEqual(kwargs.get('start_time'), expected_start_time)
        
        if expected_end_time is not None:
            self.assertEqual(kwargs.get('end_time'), expected_end_time)


class PerformanceTestUtils:
    """Утилиты для тестирования производительности"""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """
        Измеряет время выполнения функции.
        
        Args:
            func: функция для измерения
            *args: аргументы функции
            **kwargs: именованные аргументы функции
        
        Returns:
            tuple: (result, execution_time_seconds)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    def assert_execution_time_under(test_case, max_seconds, func, *args, **kwargs):
        """
        Проверяет, что функция выполняется быстрее заданного времени.
        
        Args:
            test_case: экземпляр TestCase
            max_seconds: максимальное время выполнения в секундах
            func: функция для тестирования
            *args: аргументы функции
            **kwargs: именованные аргументы функции
        
        Returns:
            результат выполнения функции
        """
        result, execution_time = PerformanceTestUtils.measure_execution_time(func, *args, **kwargs)
        test_case.assertLessEqual(
            execution_time, 
            max_seconds,
            f"Функция выполнялась {execution_time:.2f} секунд, "
            f"что больше ожидаемых {max_seconds} секунд"
        )
        return result


def run_performance_tests():
    """Запускает набор тестов производительности"""
    print("Запуск тестов производительности...")
    
    # Тест производительности создания тестовых файлов
    print("1. Тест создания тестовых файлов:")
    
    start_time = time.time()
    small_file = VideoFileGenerator.create_small_video_file(size_kb=100)
    small_file_time = time.time() - start_time
    print(f"   - Малый файл (100KB): {small_file_time:.4f} сек")
    
    # Тест создания большого файла (осторожно с памятью!)
    print("2. Тест создания большого файла:")
    start_time = time.time()
    try:
        large_file = VideoFileGenerator.create_large_video_file(size_mb=10)  # 10MB для теста
        large_file_time = time.time() - start_time
        print(f"   - Большой файл (10MB): {large_file_time:.4f} сек")
    except MemoryError:
        print("   - Большой файл: Недостаточно памяти")
    
    print("3. Тест MockVideoConverter:")
    mock_converter = MockVideoConverter(conversion_time=0.05)  # 50ms
    
    start_time = time.time()
    temp_output = tempfile.NamedTemporaryFile(suffix='.gif', delete=False).name
    result = mock_converter.convert_video_to_gif(small_file, temp_output)
    mock_time = time.time() - start_time
    print(f"   - Мок-конвертация: {mock_time:.4f} сек, результат: {result}")
    
    # Очищаем временный файл
    if os.path.exists(temp_output):
        os.unlink(temp_output)
    
    print("Тесты производительности завершены.")


def create_test_video_file(filename="test.mp4", content_type="video/mp4", size_kb=50):
    """
    Быстрая функция для создания тестового видеофайла.
    
    Args:
        filename: имя файла
        content_type: MIME тип
        size_kb: размер в килобайтах
    
    Returns:
        SimpleUploadedFile: тестовый файл
    """
    return VideoFileGenerator.create_small_video_file(filename, size_kb)


# Предустановленные тестовые данные
COMMON_VIDEO_FORMATS = [
    'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v'
]

INVALID_FILE_FORMATS = [
    'txt', 'jpg', 'png', 'pdf', 'doc', 'zip', 'exe'
]

CONVERSION_QUALITY_PRESETS = {
    'low': {'width': 480, 'fps': 15},
    'medium': {'width': 720, 'fps': 24},
    'high': {'width': 1080, 'fps': 30},
    'ultra': {'width': 1440, 'fps': 60},
}

# Словарь типичных ошибок для тестирования
TEST_ERROR_SCENARIOS = {
    'file_too_large': {
        'error_type': 'ValidationError',
        'message': 'Размер файла слишком большой',
        'setup': lambda: VideoFileGenerator.create_large_video_file(size_mb=600)
    },
    'invalid_format': {
        'error_type': 'ValidationError',
        'message': 'Неподдерживаемый формат файла',
        'setup': lambda: SimpleUploadedFile("test.txt", b"not a video", "text/plain")
    },
    'conversion_failed': {
        'error_type': 'RuntimeError', 
        'message': 'Ошибка при конвертации видео',
        'setup': lambda: MockVideoConverter(should_succeed=False)
    }
}


if __name__ == '__main__':
    # Запуск тестов производительности при прямом вызове
    run_performance_tests()
