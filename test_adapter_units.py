#!/usr/bin/env python
"""
Комплексные unit-тесты для адаптеров конвертации файлов.
Тестирует каждый адаптер изолированно с mock-данными.
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import io

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

# Импорт тестируемых компонентов
from converter.adapters.base import BaseEngine, ConversionResult, EngineNotAvailableError, ConversionError
from converter.adapters.video_engine import VideoEngine
from converter.adapters.image_engine import ImageEngine
from converter.adapters.audio_engine import AudioEngine
from converter.adapters.document_engine import DocumentEngine
from converter.adapters.archive_engine import ArchiveEngine
from converter.adapters.engine_manager import EngineManager


class TestConversionResult(unittest.TestCase):
    """Тесты для класса ConversionResult."""

    def test_successful_result(self):
        """Тест создания успешного результата."""
        result = ConversionResult(
            success=True,
            output_path="/path/to/output.gif",
            metadata={"duration": 10.5, "fps": 15}
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.output_path, "/path/to/output.gif")
        self.assertIsNone(result.error_message)
        self.assertEqual(result.metadata["duration"], 10.5)
        self.assertEqual(result.metadata["fps"], 15)

    def test_error_result(self):
        """Тест создания результата с ошибкой."""
        result = ConversionResult(
            success=False,
            error_message="Conversion failed"
        )
        
        self.assertFalse(result.success)
        self.assertIsNone(result.output_path)
        self.assertEqual(result.error_message, "Conversion failed")
        self.assertEqual(result.metadata, {})

    def test_default_metadata(self):
        """Тест инициализации пустых метаданных."""
        result = ConversionResult(success=True)
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.metadata, dict)
        self.assertEqual(len(result.metadata), 0)


class TestBaseEngine(unittest.TestCase):
    """Тесты для базового класса BaseEngine."""

    def setUp(self):
        """Создаем конкретную реализацию BaseEngine для тестирования."""
        class TestEngine(BaseEngine):
            def convert(self, input_file, output_path, **kwargs):
                return ConversionResult(success=True, output_path=str(output_path))
            
            def get_supported_formats(self):
                return {'input': ['test'], 'output': ['test']}
            
            def validate_input(self, input_file):
                return True

        self.engine = TestEngine(test_param="test_value")

    def test_initialization(self):
        """Тест инициализации адаптера."""
        self.assertEqual(self.engine.config["test_param"], "test_value")
        self.assertIsNotNone(self.engine.logger)

    def test_get_file_info_with_django_file(self):
        """Тест получения информации о Django UploadedFile."""
        mock_file = Mock()
        mock_file.name = "test.mp4"
        mock_file.size = 1024
        mock_file.content_type = "video/mp4"
        
        info = self.engine.get_file_info(mock_file)
        
        self.assertEqual(info['name'], 'test.mp4')
        self.assertEqual(info['size'], 1024)
        self.assertEqual(info['content_type'], 'video/mp4')

    def test_get_file_info_with_path(self):
        """Тест получения информации о файле по пути."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_path = temp_file.name
        
        try:
            info = self.engine.get_file_info(temp_path)
            
            self.assertEqual(info['name'], Path(temp_path).name)
            self.assertEqual(info['size'], 12)  # len(b"test content")
        finally:
            os.unlink(temp_path)

    def test_cleanup_temp_files(self):
        """Тест очистки временных файлов."""
        # Создаем временные файлы
        temp_files = []
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.close()
            temp_files.append(temp_file.name)
        
        # Проверяем, что файлы существуют
        for temp_path in temp_files:
            self.assertTrue(os.path.exists(temp_path))
        
        # Очищаем файлы
        self.engine.cleanup_temp_files(temp_files)
        
        # Проверяем, что файлы удалены
        for temp_path in temp_files:
            self.assertFalse(os.path.exists(temp_path))

    def test_check_dependencies_default(self):
        """Тест проверки зависимостей по умолчанию."""
        deps = self.engine.check_dependencies()
        self.assertIsInstance(deps, dict)
        self.assertTrue(deps['base'])


class TestVideoEngine(unittest.TestCase):
    """Тесты для VideoEngine."""

    def setUp(self):
        self.engine = VideoEngine()

    def test_initialization(self):
        """Тест инициализации VideoEngine."""
        # Тест с MoviePy
        engine_moviepy = VideoEngine(use_moviepy=True)
        self.assertTrue(engine_moviepy.use_moviepy)
        
        # Тест без MoviePy
        engine_ffmpeg = VideoEngine(use_moviepy=False)
        self.assertFalse(engine_ffmpeg.use_moviepy)

    def test_supported_formats(self):
        """Тест получения поддерживаемых форматов."""
        formats = self.engine.get_supported_formats()
        
        self.assertIn('input', formats)
        self.assertIn('output', formats)
        self.assertIn('mp4', formats['input'])
        self.assertIn('gif', formats['output'])

    def test_validate_input(self):
        """Тест валидации входных файлов."""
        # Валидный видеофайл
        mock_video = Mock()
        mock_video.name = "test.mp4"
        self.assertTrue(self.engine.validate_input(mock_video))
        
        # Невалидный файл
        mock_text = Mock()
        mock_text.name = "test.txt"
        self.assertFalse(self.engine.validate_input(mock_text))

    @patch('converter.adapters.video_engine.shutil.which')
    def test_check_dependencies(self, mock_which):
        """Тест проверки зависимостей."""
        # FFmpeg доступен
        mock_which.side_effect = lambda x: "/usr/bin/ffmpeg" if x == "ffmpeg" else None
        deps = self.engine.check_dependencies()
        self.assertTrue(deps['ffmpeg'])
        
        # FFmpeg недоступен
        mock_which.return_value = None
        deps = self.engine.check_dependencies()
        self.assertFalse(deps['ffmpeg'])

    @patch('converter.adapters.video_engine.shutil.which')
    def test_is_available(self, mock_which):
        """Тест проверки доступности адаптера."""
        # FFmpeg доступен
        mock_which.side_effect = lambda x: "/usr/bin/ffmpeg" if x == "ffmpeg" else None
        self.assertTrue(self.engine.is_available())
        
        # FFmpeg недоступен
        mock_which.return_value = None
        self.assertFalse(self.engine.is_available())

    @patch('converter.adapters.video_engine.get_video_info')
    def test_get_video_info(self, mock_get_info):
        """Тест получения информации о видео."""
        mock_info = {
            'duration': 10.5,
            'fps': 30,
            'width': 1920,
            'height': 1080
        }
        mock_get_info.return_value = mock_info
        
        mock_file = Mock()
        mock_file.name = "test.mp4"
        
        info = self.engine.get_video_info(mock_file)
        self.assertEqual(info, mock_info)

    def test_validate_conversion_params(self):
        """Тест валидации параметров конвертации."""
        # Валидные параметры
        params = {'fps': 15, 'width': 320, 'start_time': 0}
        validated = self.engine._validate_conversion_params(params)
        self.assertEqual(validated['fps'], 15)
        self.assertEqual(validated['width'], 320)
        
        # Параметры с ограничениями
        params = {'fps': 100, 'width': 10}  # Слишком большой FPS, слишком маленькая ширина
        validated = self.engine._validate_conversion_params(params)
        self.assertLessEqual(validated['fps'], 60)  # Должен быть ограничен
        self.assertGreaterEqual(validated['width'], 50)  # Должен быть увеличен


class TestImageEngine(unittest.TestCase):
    """Тесты для ImageEngine."""

    def setUp(self):
        self.engine = ImageEngine()

    def test_supported_formats(self):
        """Тест поддерживаемых форматов изображений."""
        formats = self.engine.get_supported_formats()
        
        self.assertIn('input', formats)
        self.assertIn('output', formats)
        self.assertIn('jpg', formats['input'])
        self.assertIn('png', formats['output'])

    def test_validate_input(self):
        """Тест валидации входных изображений."""
        # Валидное изображение
        mock_image = Mock()
        mock_image.name = "test.jpg"
        self.assertTrue(self.engine.validate_input(mock_image))
        
        # Невалидный файл
        mock_video = Mock()
        mock_video.name = "test.mp4"
        self.assertFalse(self.engine.validate_input(mock_video))

    @patch('converter.adapters.image_engine.PIL.Image')
    def test_check_dependencies(self, mock_pil):
        """Тест проверки зависимостей."""
        # PIL доступен
        mock_pil.open = Mock()
        deps = self.engine.check_dependencies()
        self.assertTrue(deps['PIL'])


class TestAudioEngine(unittest.TestCase):
    """Тесты для AudioEngine."""

    def setUp(self):
        self.engine = AudioEngine()

    def test_supported_formats(self):
        """Тест поддерживаемых аудиоформатов."""
        formats = self.engine.get_supported_formats()
        
        self.assertIn('input', formats)
        self.assertIn('output', formats)
        self.assertIn('mp3', formats['input'])
        self.assertIn('wav', formats['output'])

    def test_validate_input(self):
        """Тест валидации аудиофайлов."""
        # Валидный аудиофайл
        mock_audio = Mock()
        mock_audio.name = "test.mp3"
        self.assertTrue(self.engine.validate_input(mock_audio))
        
        # Невалидный файл
        mock_image = Mock()
        mock_image.name = "test.jpg"
        self.assertFalse(self.engine.validate_input(mock_image))


class TestDocumentEngine(unittest.TestCase):
    """Тесты для DocumentEngine."""

    def setUp(self):
        self.engine = DocumentEngine()

    def test_supported_formats(self):
        """Тест поддерживаемых форматов документов."""
        formats = self.engine.get_supported_formats()
        
        self.assertIn('input', formats)
        self.assertIn('output', formats)
        self.assertIn('pdf', formats['input'])
        self.assertIn('txt', formats['output'])

    def test_validate_input(self):
        """Тест валидации документов."""
        # Валидный документ
        mock_doc = Mock()
        mock_doc.name = "test.pdf"
        self.assertTrue(self.engine.validate_input(mock_doc))
        
        # Невалидный файл
        mock_audio = Mock()
        mock_audio.name = "test.mp3"
        self.assertFalse(self.engine.validate_input(mock_audio))


class TestArchiveEngine(unittest.TestCase):
    """Тесты для ArchiveEngine."""

    def setUp(self):
        self.engine = ArchiveEngine()

    def test_supported_formats(self):
        """Тест поддерживаемых форматов архивов."""
        formats = self.engine.get_supported_formats()
        
        self.assertIn('input', formats)
        self.assertIn('output', formats)
        self.assertIn('zip', formats['input'])
        self.assertIn('tar', formats['output'])

    def test_validate_input(self):
        """Тест валидации архивов."""
        # Валидный архив
        mock_archive = Mock()
        mock_archive.name = "test.zip"
        self.assertTrue(self.engine.validate_input(mock_archive))
        
        # Невалидный файл
        mock_doc = Mock()
        mock_doc.name = "test.pdf"
        self.assertFalse(self.engine.validate_input(mock_doc))


class TestEngineManager(unittest.TestCase):
    """Тесты для EngineManager."""

    def setUp(self):
        self.manager = EngineManager()

    def test_initialization(self):
        """Тест инициализации менеджера."""
        self.assertIsInstance(self.manager.engines, dict)
        self.assertEqual(len(self.manager.engines), 0)  # Изначально пуст

    def test_register_engine(self):
        """Тест регистрации адаптеров."""
        mock_engine = Mock()
        self.manager.register_engine('test', mock_engine)
        
        self.assertIn('test', self.manager.engines)
        self.assertEqual(self.manager.engines['test'], mock_engine)

    def test_get_engine(self):
        """Тест получения адаптеров."""
        # Существующий адаптер
        video_engine = self.manager.get_engine('video')
        self.assertIsInstance(video_engine, VideoEngine)
        
        # Кеширование
        video_engine_2 = self.manager.get_engine('video')
        self.assertIs(video_engine, video_engine_2)
        
        # Несуществующий адаптер
        unknown_engine = self.manager.get_engine('unknown')
        self.assertIsNone(unknown_engine)

    def test_detect_engine_type(self):
        """Тест определения типа адаптера по расширению."""
        test_cases = [
            ('video.mp4', 'video'),
            ('image.jpg', 'image'),
            ('audio.mp3', 'audio'),
            ('document.pdf', 'document'),
            ('archive.zip', 'archive'),
            ('archive.tar.gz', 'archive'),
            ('unknown.xyz', None),
        ]
        
        for filename, expected_type in test_cases:
            with self.subTest(filename=filename):
                detected_type = self.manager.detect_engine_type(filename)
                self.assertEqual(detected_type, expected_type)

    def test_get_engine_status(self):
        """Тест получения статуса всех адаптеров."""
        status = self.manager.get_engine_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('video', status)
        self.assertIn('image', status)
        
        # Проверяем структуру статуса
        for engine_type, info in status.items():
            with self.subTest(engine_type=engine_type):
                self.assertIn('available', info)
                self.assertIn('dependencies', info)
                self.assertIn('supported_formats', info)

    def test_get_supported_formats(self):
        """Тест получения поддерживаемых форматов."""
        formats = self.manager.get_supported_formats()
        
        self.assertIsInstance(formats, dict)
        self.assertIn('video', formats)
        self.assertIn('image', formats)


class TestAdapterIntegration(unittest.TestCase):
    """Интеграционные тесты адаптеров."""

    def setUp(self):
        self.manager = EngineManager()

    def test_video_to_gif_workflow(self):
        """Тест полного workflow конвертации видео в GIF."""
        # Создаем mock видеофайл
        mock_video = Mock()
        mock_video.name = "test.mp4"
        mock_video.size = 1024 * 1024  # 1MB
        
        # Получаем видео адаптер
        video_engine = self.manager.get_engine('video')
        self.assertIsNotNone(video_engine)
        
        # Проверяем валидацию
        self.assertTrue(video_engine.validate_input(mock_video))
        
        # Проверяем поддерживаемые форматы
        formats = video_engine.get_supported_formats()
        self.assertIn('mp4', formats['input'])
        self.assertIn('gif', formats['output'])

    def test_error_handling(self):
        """Тест обработки ошибок в адаптерах."""
        # Создаем адаптер с mock, который всегда падает
        class FailingEngine(BaseEngine):
            def convert(self, input_file, output_path, **kwargs):
                raise ConversionError("Conversion failed")
            
            def get_supported_formats(self):
                return {'input': ['fail'], 'output': ['fail']}
            
            def validate_input(self, input_file):
                return True

        failing_engine = FailingEngine()
        
        # Проверяем, что исключение правильно обрабатывается
        with self.assertRaises(ConversionError):
            failing_engine.convert("input", "output")

    def test_engine_availability_check(self):
        """Тест проверки доступности адаптеров."""
        all_engines = ['video', 'image', 'audio', 'document', 'archive']
        
        for engine_type in all_engines:
            with self.subTest(engine_type=engine_type):
                engine = self.manager.get_engine(engine_type)
                self.assertIsNotNone(engine)
                
                # Проверяем метод проверки доступности
                is_available = engine.is_available()
                self.assertIsInstance(is_available, bool)
                
                # Проверяем зависимости
                deps = engine.check_dependencies()
                self.assertIsInstance(deps, dict)


def create_test_suite():
    """Создает набор тестов."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Добавляем все тест-классы
    test_classes = [
        TestConversionResult,
        TestBaseEngine,
        TestVideoEngine,
        TestImageEngine,
        TestAudioEngine,
        TestDocumentEngine,
        TestArchiveEngine,
        TestEngineManager,
        TestAdapterIntegration,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


def main():
    """Главная функция запуска тестов."""
    print("Запуск комплексных unit-тестов адаптеров")
    print("=" * 60)
    
    # Создаем и запускаем тесты
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Выводим результаты
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("[OK] Все тесты прошли!")
        print(f"Выполнено тестов: {result.testsRun}")
    else:
        print("[FAIL] Некоторые тесты провалились!")
        print(f"Выполнено тестов: {result.testsRun}")
        print(f"Ошибок: {len(result.errors)}")
        print(f"Провалов: {len(result.failures)}")
        
        # Выводим детали ошибок
        for test, error in result.errors:
            print(f"\nОШИБКА в {test}:")
            print(error)
        
        for test, failure in result.failures:
            print(f"\nПРОВАЛ в {test}:")
            print(failure)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
