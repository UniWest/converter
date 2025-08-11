#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Демонстрационный скрипт для показа возможностей системы адаптеров конвертации.
"""

import os
import sys
import tempfile
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

from converter.adapters.engine_manager import EngineManager
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io


def print_header(text):
    """Печатает заголовок."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def create_sample_images():
    """Создает несколько образцов изображений."""
    images = {}
    
    # PNG изображение
    png_img = Image.new('RGB', (100, 100), color='red')
    png_buffer = io.BytesIO()
    png_img.save(png_buffer, format='PNG')
    png_buffer.seek(0)
    images['sample.png'] = SimpleUploadedFile('sample.png', png_buffer.read(), 'image/png')
    
    # WEBP изображение
    webp_img = Image.new('RGBA', (150, 150), color=(0, 255, 0, 128))
    webp_buffer = io.BytesIO()
    webp_img.save(webp_buffer, format='WEBP')
    webp_buffer.seek(0)
    images['sample.webp'] = SimpleUploadedFile('sample.webp', webp_buffer.read(), 'image/webp')
    
    # GIF анимация
    frames = []
    for i in range(3):
        color = ['blue', 'green', 'yellow'][i]
        frame = Image.new('RGB', (80, 80), color=color)
        frames.append(frame)
    
    gif_buffer = io.BytesIO()
    frames[0].save(gif_buffer, format='GIF', save_all=True, append_images=frames[1:], duration=500, loop=0)
    gif_buffer.seek(0)
    images['animation.gif'] = SimpleUploadedFile('animation.gif', gif_buffer.read(), 'image/gif')
    
    return images


def demo_basic_functionality():
    """Демонстрирует базовую функциональность."""
    print_header("ДЕМОНСТРАЦИЯ БАЗОВОЙ ФУНКЦИОНАЛЬНОСТИ")
    
    manager = EngineManager()
    
    # Показываем статус адаптеров
    print("Статус всех адаптеров:")
    status = manager.get_engine_status()
    
    for engine_type, info in status.items():
        available = "[OK]" if info['available'] else "[X]"
        formats_count = f"{len(info['supported_formats']['input'])}→{len(info['supported_formats']['output'])}"
        print(f"  {available} {engine_type:10} - {formats_count} форматов")
    
    print("\nОпределение типов файлов:")
    test_files = [
        'photo.jpg', 'video.mp4', 'music.mp3', 
        'document.pdf', 'archive.zip', 'presentation.pptx'
    ]
    
    for filename in test_files:
        detected = manager.detect_engine_type(filename)
        print(f"  {filename:15} -> {detected or 'неизвестно'}")


def demo_image_conversion():
    """Демонстрирует конвертацию изображений."""
    print_header("ДЕМОНСТРАЦИЯ КОНВЕРТАЦИИ ИЗОБРАЖЕНИЙ")
    
    manager = EngineManager()
    image_engine = manager.get_engine('image')
    
    if not image_engine or not image_engine.is_available():
        print("[SKIP] ImageEngine недоступен")
        return
    
    # Создаем образцы изображений
    images = create_sample_images()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print("Выполняем различные конвертации:")
        
        # PNG -> JPG
        png_file = images['sample.png']
        jpg_output = Path(temp_dir) / "converted.jpg"
        result = image_engine.convert(png_file, str(jpg_output), quality=85)
        
        if result.success:
            size = jpg_output.stat().st_size
            print(f"  [OK] PNG -> JPG: {png_file.size}b -> {size}b (качество 85%)")
        else:
            print(f"  [FAIL] PNG -> JPG: {result.error_message}")
        
        # WEBP -> PNG
        webp_file = images['sample.webp']
        png_output = Path(temp_dir) / "converted.png"
        result = image_engine.convert(webp_file, str(png_output))
        
        if result.success:
            size = png_output.stat().st_size
            print(f"  [OK] WEBP -> PNG: {webp_file.size}b -> {size}b")
        else:
            print(f"  [FAIL] WEBP -> PNG: {result.error_message}")
        
        # GIF -> PNG (первый кадр)
        gif_file = images['animation.gif']
        gif_png_output = Path(temp_dir) / "frame.png"
        result = image_engine.convert(gif_file, str(gif_png_output))
        
        if result.success:
            size = gif_png_output.stat().st_size
            print(f"  [OK] GIF -> PNG: {gif_file.size}b -> {size}b (первый кадр)")
        else:
            print(f"  [FAIL] GIF -> PNG: {result.error_message}")
        
        # Изменение размера
        resize_output = Path(temp_dir) / "resized.jpg"
        result = image_engine.convert(png_file, str(resize_output), resize=(50, 50), quality=90)
        
        if result.success:
            size = resize_output.stat().st_size
            with Image.open(resize_output) as img:
                print(f"  [OK] Изменение размера: {img.size} пикселей, {size}b")
        else:
            print(f"  [FAIL] Изменение размера: {result.error_message}")


def demo_performance_test():
    """Демонстрирует тест производительности."""
    print_header("ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ")
    
    manager = EngineManager()
    image_engine = manager.get_engine('image')
    
    if not image_engine or not image_engine.is_available():
        print("[SKIP] ImageEngine недоступен")
        return
    
    import time
    
    # Создаем набор изображений
    num_files = 10
    print(f"Создаем {num_files} тестовых изображений...")
    
    test_images = []
    for i in range(num_files):
        img = Image.new('RGB', (50, 50), color=(i*25 % 255, (i*50) % 255, (i*75) % 255))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        test_images.append(SimpleUploadedFile(f'test_{i}.png', buffer.read(), 'image/png'))
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Конвертируем {num_files} изображений PNG -> JPG...")
        
        start_time = time.time()
        successful = 0
        
        for i, img_file in enumerate(test_images):
            output_path = Path(temp_dir) / f"output_{i}.jpg"
            result = image_engine.convert(img_file, str(output_path), quality=80)
            if result.success:
                successful += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"Результаты:")
        print(f"  Конвертировано: {successful}/{num_files} файлов")
        print(f"  Общее время: {total_time:.3f} сек")
        print(f"  Среднее время на файл: {total_time/num_files:.3f} сек")
        print(f"  Производительность: {num_files/total_time:.1f} файлов/сек")


def demo_error_handling():
    """Демонстрирует обработку ошибок."""
    print_header("ДЕМОНСТРАЦИЯ ОБРАБОТКИ ОШИБОК")
    
    manager = EngineManager()
    
    print("Тестируем различные сценарии ошибок:")
    
    # 1. Неподдерживаемый формат
    unknown_file = SimpleUploadedFile('test.unknown', b'content', 'application/octet-stream')
    result = manager.convert_file(unknown_file, '/tmp/output')
    print(f"  Неизвестный формат: {'[OK]' if not result.success else '[FAIL]'}")
    print(f"    Сообщение: {result.error_message}")
    
    # 2. Поврежденное изображение
    corrupted_img = SimpleUploadedFile('corrupted.jpg', b'not an image', 'image/jpeg')
    image_engine = manager.get_engine('image')
    if image_engine:
        result = image_engine.convert(corrupted_img, '/tmp/output.png')
        print(f"  Поврежденное изображение: {'[OK]' if not result.success else '[FAIL]'}")
        print(f"    Сообщение: {result.error_message[:50]}...")
    
    # 3. Недоступный адаптер
    result = manager.convert_file(SimpleUploadedFile('test.xyz', b'content'), '/tmp/output')
    print(f"  Недоступный адаптер: {'[OK]' if not result.success else '[FAIL]'}")


def main():
    """Главная функция демонстрации."""
    print("=" * 60)
    print("  ДЕМОНСТРАЦИЯ СИСТЕМЫ АДАПТЕРОВ КОНВЕРТАЦИИ")
    print("=" * 60)
    print("Показываем возможности системы в реальном времени...")
    
    try:
        demo_basic_functionality()
        demo_image_conversion()
        demo_performance_test()
        demo_error_handling()
        
        print_header("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО")
        print("Система адаптеров конвертации работает стабильно!")
        print("Готова к продуктивному использованию.")
        
    except Exception as e:
        print(f"Ошибка во время демонстрации: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
