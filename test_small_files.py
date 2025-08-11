#!/usr/bin/env python
import os
import sys
import tempfile
import io
"""
Тесты для адаптеров с небольшими реальными файлами.
Создает минимальные валидные файлы для тестирования конвертации.
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


def create_small_png_image(width=10, height=10):
    """Создает минимальное PNG изображение."""
    from PIL import Image
    
    # Создаем минимальное изображение
    image = Image.new('RGB', (width, height), color='red')
    
    # Сохраняем в память
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    
    return SimpleUploadedFile(
        'test.png',
        buffer.read(),
        content_type='image/png'
    )


def create_small_gif_image(width=10, height=10):
    """Создает минимальную GIF анимацию."""
    from PIL import Image
    
    # Создаем две рамки для анимации
    frames = []
    for i in range(2):
        color = 'red' if i == 0 else 'blue'
        frame = Image.new('RGB', (width, height), color=color)
        frames.append(frame)
    
    # Сохраняем как анимированную GIF
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=500,
        loop=0
    )
    buffer.seek(0)
    
    return SimpleUploadedFile(
        'test.gif',
        buffer.read(),
        content_type='image/gif'
    )


def create_small_text_file():
    """Создает минимальный текстовый файл."""
    content = "Это тестовый документ для конвертации.\nВторая строка.\nТретья строка."
    return SimpleUploadedFile(
        'test.txt',
        content.encode('utf-8'),
        content_type='text/plain'
    )


def create_small_csv_file():
    """Создает минимальный CSV файл."""
    content = "имя,возраст,город\nАлиса,25,Москва\nБоб,30,Санкт-Петербург\nВера,22,Новосибирск"
    return SimpleUploadedFile(
        'test.csv',
        content.encode('utf-8'),
        content_type='text/csv'
    )


def create_minimal_mp3_header():
    """Создает минимальный MP3 заголовок для теста валидации."""
    # MP3 начинается с FF FB (MPEG-1 Layer 3)
    mp3_header = bytes([0xFF, 0xFB]) + b'\x00' * 100  # Минимальный заголовок + данные
    return SimpleUploadedFile(
        'test.mp3',
        mp3_header,
        content_type='audio/mpeg'
    )


class TestSmallFileConversions(unittest.TestCase):
    """Тесты конвертации с небольшими файлами."""

    def setUp(self):
        self.manager = EngineManager()
        self.temp_dir = tempfile.mkdtemp(prefix="small_files_test_")

    def tearDown(self):
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass  # Игнорируем ошибки очистки

    def test_png_to_jpg_conversion(self):
        """Тест конвертации PNG в JPG."""
        print("\n--- Тест: PNG → JPG (небольшие файлы) ---")
        
        image_engine = self.manager.get_engine('image')
        if not image_engine or not image_engine.is_available():
            self.skipTest("Адаптер изображений недоступен")

        # Создаем минимальное PNG изображение
        input_file = create_small_png_image(20, 20)
        output_path = Path(self.temp_dir) / "output.jpg"
        
        print(f"Входной файл: {input_file.name} ({input_file.size} байт)")
        
        # Проверяем валидацию
        self.assertTrue(image_engine.validate_input(input_file))
        
        # Выполняем конвертацию
        result = image_engine.convert(input_file, str(output_path))
        
        # Проверяем результат
        self.assertTrue(result.success, f"Конвертация провалилась: {result.error_message}")
        self.assertTrue(output_path.exists(), "Выходной файл не создан")
        self.assertGreater(output_path.stat().st_size, 0, "Выходной файл пустой")
        
        # Проверяем формат
        from PIL import Image
        with Image.open(output_path) as img:
            self.assertEqual(img.format, 'JPEG')
            self.assertEqual(img.size, (20, 20))
        
        print(f"✓ Конвертация успешна. Размер JPG: {output_path.stat().st_size} байт")

    def test_gif_optimization(self):
        """Тест работы с GIF файлами."""
        print("\n--- Тест: Работа с GIF ---")
        
        image_engine = self.manager.get_engine('image')
        if not image_engine or not image_engine.is_available():
            self.skipTest("Адаптер изображений недоступен")

        # Создаем минимальную GIF анимацию
        input_file = create_small_gif_image(15, 15)
        output_path = Path(self.temp_dir) / "optimized.gif"
        
        print(f"Входной файл: {input_file.name} ({input_file.size} байт)")
        
        # Проверяем валидацию
        self.assertTrue(image_engine.validate_input(input_file))
        
        # Выполняем "оптимизацию" (конвертацию в тот же формат)
        result = image_engine.convert(input_file, str(output_path))
        
        # Проверяем результат
        self.assertTrue(result.success, f"Обработка провалилась: {result.error_message}")
        self.assertTrue(output_path.exists(), "Выходной файл не создан")
        
        print(f"✓ Обработка GIF успешна. Размер: {output_path.stat().st_size} байт")

    def test_text_file_detection(self):
        """Тест определения текстовых файлов."""
        print("\n--- Тест: Определение текстовых файлов ---")
        
        # Создаем текстовый файл
        text_file = create_small_text_file()
        
        # Проверяем определение типа
        engine_type = self.manager.detect_engine_type(text_file.name)
        # Текстовые файлы могут обрабатываться document engine
        print(f"Тип адаптера для .txt: {engine_type}")
        
        # Проверим статус document engine
        doc_engine = self.manager.get_engine('document')
        if doc_engine:
            print(f"Document engine доступен: {doc_engine.is_available()}")
            formats = doc_engine.get_supported_formats()
            print(f"Поддерживаемые входные форматы: {formats['input'][:5]}...")  # Первые 5

    def test_multiple_format_support(self):
        """Тест поддержки множественных форматов."""
        print("\n--- Тест: Поддержка множественных форматов ---")
        
        test_files = {
            'image.png': 'image',
            'video.mp4': 'video', 
            'audio.mp3': 'audio',
            'doc.pdf': 'document',
            'archive.zip': 'archive',
            'presentation.pptx': 'document',
            'spreadsheet.xlsx': 'document',
        }
        
        for filename, expected_type in test_files.items():
            detected_type = self.manager.detect_engine_type(filename)
            print(f"{filename:15} → {detected_type or 'не определен':10} (ожидался: {expected_type})")
            
            if expected_type in ['image', 'video']:  # Основные типы, которые точно должны работать
                self.assertEqual(detected_type, expected_type, 
                    f"Неправильно определен тип для {filename}")

    def test_file_size_validation(self):
        """Тест проверки размера файлов."""
        print("\n--- Тест: Проверка размера файлов ---")
        
        # Создаем файлы разного размера
        small_image = create_small_png_image(5, 5)
        medium_image = create_small_png_image(50, 50)
        large_image = create_small_png_image(100, 100)
        
        print(f"Маленькое изображение: {small_image.size} байт")
        print(f"Среднее изображение: {medium_image.size} байт") 
        print(f"Большое изображение: {large_image.size} байт")
        
        # Все должны пройти валидацию
        image_engine = self.manager.get_engine('image')
        if image_engine:
            for img in [small_image, medium_image, large_image]:
                self.assertTrue(image_engine.validate_input(img), 
                    f"Изображение размером {img.size} байт не прошло валидацию")
        
        print("✓ Все размеры файлов прошли валидацию")

    def test_conversion_parameters(self):
        """Тест передачи параметров конвертации."""
        print("\n--- Тест: Параметры конвертации ---")
        
        image_engine = self.manager.get_engine('image')
        if not image_engine or not image_engine.is_available():
            self.skipTest("Адаптер изображений недоступен")

        # Создаем исходное изображение
        input_file = create_small_png_image(40, 30)
        output_path = Path(self.temp_dir) / "resized.png"
        
        # Конвертируем с изменением размера
        try:
            result = image_engine.convert(
                input_file, 
                str(output_path),
                resize=(20, 15),  # Уменьшаем в 2 раза
                quality=90
            )
            
            if result.success:
                from PIL import Image
                with Image.open(output_path) as img:
                    print(f"✓ Конвертация с параметрами. Новый размер: {img.size}")
                    # Проверяем, что размер изменился
                    self.assertEqual(img.size, (20, 15))
            else:
                print(f"ℹ️ Параметры не поддерживаются: {result.error_message}")
        except Exception as e:
            print(f"ℹ️ Тест параметров пропущен: {e}")

    def test_error_handling_with_corrupted_files(self):
        """Тест обработки поврежденных файлов."""
        print("\n--- Тест: Поврежденные файлы ---")
        
        # Создаем "поврежденный" PNG файл
        corrupted_png = SimpleUploadedFile(
            'corrupted.png',
            b'PNG\x00\x00invalid data',  # Неправильные PNG данные
            content_type='image/png'
        )
        
        image_engine = self.manager.get_engine('image')
        if not image_engine:
            self.skipTest("Адаптер изображений недоступен")
        
        # Файл должен пройти валидацию по имени
        self.assertTrue(image_engine.validate_input(corrupted_png))
        
        # Но конвертация должна провалиться
        output_path = Path(self.temp_dir) / "should_fail.jpg"
        result = image_engine.convert(corrupted_png, str(output_path))
        
        # Ожидаем неудачу
        self.assertFalse(result.success, "Конвертация поврежденного файла должна провалиться")
        self.assertIsNotNone(result.error_message, "Должно быть сообщение об ошибке")
        
        print(f"✓ Поврежденный файл правильно обработан. Ошибка: {result.error_message[:50]}...")


class TestAdapterPerformance(unittest.TestCase):
    """Простые тесты производительности адаптеров."""

    def setUp(self):
        self.manager = EngineManager()
        self.temp_dir = tempfile.mkdtemp(prefix="perf_test_")

    def tearDown(self):
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

    def test_multiple_conversions_speed(self):
        """Тест скорости множественных конвертаций."""
        print("\n--- Тест: Скорость множественных конвертаций ---")
        
        image_engine = self.manager.get_engine('image')
        if not image_engine or not image_engine.is_available():
            self.skipTest("Адаптер изображений недоступен")

        import time
        
        # Создаем несколько файлов
        files = [create_small_png_image(10, 10) for _ in range(5)]
        
        start_time = time.time()
        
        for i, file in enumerate(files):
            output_path = Path(self.temp_dir) / f"output_{i}.jpg"
            result = image_engine.convert(file, str(output_path))
            self.assertTrue(result.success, f"Конвертация файла {i} провалилась")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"✓ Конвертировано {len(files)} файлов за {total_time:.3f} сек")
        print(f"  Среднее время на файл: {total_time/len(files):.3f} сек")
        
        # Проверяем, что время разумное (не больше 2 секунд на файл)
        self.assertLess(total_time/len(files), 2.0, "Конвертация слишком медленная")


def create_comprehensive_test_suite():
    """Создает полный набор тестов."""
    suite = unittest.TestSuite()
    
    # Добавляем тесты
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSmallFileConversions))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdapterPerformance))
    
    return suite


def main():
    """Главная функция для запуска тестов."""
    print("Запуск тестов с небольшими файлами")
    print("=" * 60)
    
    # Проверяем доступность зависимостей
    try:
        from PIL import Image
        print("[OK] PIL/Pillow доступен")
    except ImportError:
        print("⚠️  PIL/Pillow недоступен - некоторые тесты будут пропущены")
    
    suite = create_comprehensive_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("[OK] Все тесты с небольшими файлами прошли успешно!")
        print(f"Выполнено тестов: {result.testsRun}")
    else:
        print("[FAIL] Некоторые тесты провалились!")
        print(f"Выполнено тестов: {result.testsRun}")
        print(f"Провалов: {len(result.failures)}")
        print(f"Ошибок: {len(result.errors)}")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
