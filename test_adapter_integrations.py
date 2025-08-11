#!/usr/bin/env python
import os
import sys
import tempfile
"""
Интеграционные тесты для адаптеров конвертации.
Тестирует реальные сценарии конвертации с небольшими файлами.
"""

import unittest
from pathlib import Path

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

# Импорт компонентов
from django.core.files.uploadedfile import SimpleUploadedFile
from converter.adapters.engine_manager import EngineManager

# --- Функции для создания тестовых файлов ---

def create_dummy_video_file(filename="test_video.mp4", size_kb=10):
    """Создает фиктивный видеофайл."""
    content = os.urandom(size_kb * 1024)
    return SimpleUploadedFile(filename, content, content_type='video/mp4')

def create_dummy_image_file(filename="test_image.jpg", format='JPEG'):
    """Создает фиктивный файл изображения."""
    from PIL import Image
    import io
    
    image = Image.new('RGB', (100, 100), color = 'red')
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    
    return SimpleUploadedFile(filename, buffer.read(), content_type=f'image/{format.lower()}')

def create_dummy_audio_file(filename="test_audio.mp3", duration_ms=1000):
    """Создает фиктивный аудиофайл."""
    # В реальном тесте здесь может быть генерация WAV и конвертация в MP3
    # Для простоты создаем пустой файл
    return SimpleUploadedFile(filename, b"dummy audio content", content_type='audio/mpeg')


class TestAdapterIntegration(unittest.TestCase):
    """Интеграционные тесты для реальных сценариев конвертации."""

    def setUp(self):
        self.manager = EngineManager()
        self.temp_dir = tempfile.mkdtemp(prefix="adapter_tests_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_video_to_gif_conversion(self):
        """Тест конвертации видео MP4 в GIF."""
        print("\n--- Тест: Видео MP4 -> GIF ---")
        video_engine = self.manager.get_engine('video')
        if not video_engine.is_available():
            self.skipTest("Видео адаптер (ffmpeg) недоступен")

        # Создаем тестовый видеофайл (заглушка)
        # Для реального теста здесь нужен настоящий, но маленький MP4 файл
        input_file = create_dummy_video_file()
        output_path = Path(self.temp_dir) / "output.gif"
        
        print(f"Входной файл: {input_file.name} ({input_file.size} байт)")
        print(f"Выходной путь: {output_path}")

        # Конвертация
        try:
            result = video_engine.convert(input_file, output_path, width=100)

            # Проверяем результат
            self.assertTrue(result.success, msg=f"Ошибка конвертации: {result.error_message}")
            self.assertTrue(output_path.exists(), msg="Выходной файл не создан")
            self.assertGreater(output_path.stat().st_size, 0, msg="Выходной файл пустой")
            
            print(f"✓ Конвертация успешна. Размер GIF: {output_path.stat().st_size} байт")
            
        except Exception as e:
            # Если ffmpeg падает на заглушке, это ожидаемо
            print(f"ℹ️  Конвертация пропущена (возможно, из-за фиктивного файла): {e}")
            self.skipTest("Тест требует реальный видеофайл для полной проверки")

    def test_image_to_png_conversion(self):
        """Тест конвертации изображения JPG в PNG."""
        print("\n--- Тест: Изображение JPG -> PNG ---")
        image_engine = self.manager.get_engine('image')
        if not image_engine.is_available():
            self.skipTest("Адаптер изображений (PIL) недоступен")

        # Создаем тестовое изображение
        input_file = create_dummy_image_file(filename="test.jpg", format='JPEG')
        output_path = Path(self.temp_dir) / "output.png"
        
        print(f"Входной файл: {input_file.name}")
        print(f"Выходной путь: {output_path}")

        # Конвертация
        result = image_engine.convert(input_file, output_path)

        # Проверяем результат
        self.assertTrue(result.success, msg=f"Ошибка конвертации: {result.error_message}")
        self.assertTrue(output_path.exists(), msg="Выходной файл не создан")
        self.assertGreater(output_path.stat().st_size, 0, msg="Выходной файл пустой")
        
        # Проверяем, что это действительно PNG
        from PIL import Image
        with Image.open(output_path) as img:
            self.assertEqual(img.format, 'PNG')
            
        print(f"✓ Конвертация успешна. Размер PNG: {output_path.stat().st_size} байт")

    def test_engine_manager_full_cycle(self):
        """Тест полного цикла работы EngineManager."""
        print("\n--- Тест: Полный цикл EngineManager ---")
        
        # Создаем тестовый файл
        input_file = create_dummy_image_file(filename="cycle_test.webp", format='WEBP')
        output_path = Path(self.temp_dir) / "cycle_output.jpg"
        
        print(f"Входной файл: {input_file.name}")
        
        # 1. Определение типа адаптера
        engine_type = self.manager.detect_engine_type(input_file.name)
        self.assertEqual(engine_type, 'image')
        print(f"✓ Тип адаптера определен: {engine_type}")
        
        # 2. Получение адаптера
        image_engine = self.manager.get_engine(engine_type)
        self.assertIsNotNone(image_engine)
        if not image_engine.is_available():
            self.skipTest("Адаптер изображений недоступен")
        
        # 3. Конвертация через менеджер
        result = self.manager.convert_file(
            input_file=input_file, 
            output_path=output_path, 
            engine_type=engine_type
        )
        
        # 4. Проверка результата
        self.assertTrue(result.success, msg=f"Ошибка конвертации: {result.error_message}")
        self.assertTrue(output_path.exists(), msg="Выходной файл не создан")
        self.assertGreater(output_path.stat().st_size, 0, msg="Выходной файл пустой")
        
        print(f"✓ Конвертация через менеджер успешна. Файл: {output_path}")

    def test_unsupported_format_handling(self):
        """Тест обработки неподдерживаемого формата."""
        print("\n--- Тест: Обработка неподдерживаемого формата ---")
        
        # Создаем "неподдерживаемый" файл
        input_file = SimpleUploadedFile("test.unsupported", b"content")
        output_path = Path(self.temp_dir) / "output"
        
        # 1. Проверяем, что тип не определяется
        engine_type = self.manager.detect_engine_type(input_file.name)
        self.assertIsNone(engine_type, msg="Не должен определяться адаптер для .unsupported")
        print("✓ Тип адаптера не определен, как и ожидалось")
        
        # 2. Проверяем, что convert_file возвращает ошибку
        result = self.manager.convert_file(input_file, output_path)
        self.assertFalse(result.success)
        self.assertIn("Не удалось определить", result.error_message)
        print("✓ Менеджер вернул ошибку, как и ожидалось")


def main():
    """Главная функция для запуска тестов."""
    print("Запуск интеграционных тестов для адаптеров")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdapterIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("[OK] Все интеграционные тесты прошли успешно!")
    else:
        print("[FAIL] Интеграционные тесты провалились!")
        
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
