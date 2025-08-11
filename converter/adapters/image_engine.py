"""
Адаптер для конвертации изображений.
Базовая реализация с возможностью расширения.
"""

import os
from pathlib import Path
from typing import Any, Dict, Union

from .base import BaseEngine, ConversionResult, EngineNotAvailableError, ConversionError, UnsupportedFormatError

# PIL imports для использования во всем модуле
try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageEnhance = None


class ImageEngine(BaseEngine):
    """
    Адаптер для конвертации изображений.
    Базовая реализация для будущего расширения функциональности.
    """
    
    # Поддерживаемые форматы
    SUPPORTED_INPUT_FORMATS = [
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 
        'webp', 'svg', 'ico', 'psd', 'raw', 'heic', 'heif'
    ]
    
    SUPPORTED_OUTPUT_FORMATS = [
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'ico'
    ]
    
    def __init__(self, **config):
        """
        Инициализация адаптера изображений.
        
        Args:
            **config: Параметры конфигурации
        """
        super().__init__(**config)
    
    def convert(
        self, 
        input_file: Union[str, Path, Any], 
        output_path: Union[str, Path],
        **kwargs
    ) -> ConversionResult:
        """
        Конвертирует изображение.
        
        Args:
            input_file: Входной файл изображения
            output_path: Путь для сохранения результата
            **kwargs: Параметры конвертации:
                - width: Ширина изображения
                - height: Высота изображения
                - quality: Качество сжатия (для JPEG)
                - resize_mode: Режим изменения размера ('fit', 'fill', 'stretch')
                - format: Выходной формат (если не определен по расширению)
                - create_gif: Создать анимированный GIF из статичного изображения
                - gif_duration: Длительность каждого кадра в миллисекундах (для GIF)
                - gif_loop: Количество повторений анимации (0 = бесконечно)
                - gif_frames: Количество кадров для создания эффекта
                - gif_effect: Эффект анимации ('fade', 'zoom', 'rotate', 'bounce', 'none')
                
        Returns:
            ConversionResult: Результат конвертации
        """
        try:
            # Валидация входного файла
            if not self.validate_input(input_file):
                return ConversionResult(
                    success=False,
                    error_message="Неподдерживаемый формат входного файла"
                )
            
            # Определяем выходной формат
            output_format = Path(output_path).suffix.lower().lstrip('.')
            if output_format not in self.SUPPORTED_OUTPUT_FORMATS:
                return ConversionResult(
                    success=False,
                    error_message=f"Неподдерживаемый формат выходного файла: {output_format}"
                )
            
            # Проверяем доступность PIL
            if not self.is_available():
                return ConversionResult(
                    success=False,
                    error_message="PIL/Pillow недоступен для конвертации"
                )
            
            # Используем PIL для конвертации
            from PIL import Image
            
            # Открываем исходное изображение
            if hasattr(input_file, 'read'):
                # Это Django UploadedFile или file-like объект
                image = Image.open(input_file)
            else:
                # Это путь к файлу
                image = Image.open(input_file)
            
            # Применяем параметры конвертации
            if 'resize' in kwargs:
                resize = kwargs['resize']
                if isinstance(resize, (list, tuple)) and len(resize) == 2:
                    image = image.resize(resize, Image.Resampling.LANCZOS)
            elif 'width' in kwargs or 'height' in kwargs:
                width = kwargs.get('width', image.width)
                height = kwargs.get('height', image.height)
                image = image.resize((width, height), Image.Resampling.LANCZOS)
            
            # Если нужно создать анимированный GIF из статичного изображения
            if kwargs.get('create_gif', False) and output_format.lower() == 'gif':
                return self._create_animated_gif(image, output_path, **kwargs)
            
            # Конвертируем в RGB для JPEG
            if output_format.lower() in ['jpg', 'jpeg'] and image.mode in ['RGBA', 'LA']:
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])  # Используем альфа-канал
                else:
                    background.paste(image)
                image = background
            
            # Сохраняем результат
            save_kwargs = {}
            if output_format.lower() in ['jpg', 'jpeg']:
                save_kwargs['quality'] = kwargs.get('quality', 90)
                save_kwargs['optimize'] = True
            elif output_format.lower() == 'gif':
                save_kwargs['optimize'] = True
            
            # Исправляем формат для JPEG
            pil_format = output_format.upper()
            if pil_format == 'JPG':
                pil_format = 'JPEG'
            
            image.save(output_path, format=pil_format, **save_kwargs)
            
            # Получаем метаданные
            metadata = {
                'original_size': f"{image.width}x{image.height}",
                'format': image.format or 'Unknown',
                'mode': image.mode,
            }
            
            return ConversionResult(
                success=True,
                output_path=str(output_path),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при конвертации изображения: {e}")
            return ConversionResult(
                success=False,
                error_message=f"Произошла ошибка: {str(e)}"
            )
    
    def get_supported_formats(self) -> Dict[str, list]:
        """
        Возвращает поддерживаемые форматы файлов.
        
        Returns:
            dict: Словарь с входными и выходными форматами
        """
        return {
            'input': self.SUPPORTED_INPUT_FORMATS.copy(),
            'output': self.SUPPORTED_OUTPUT_FORMATS.copy()
        }
    
    def validate_input(self, input_file: Union[str, Path, Any]) -> bool:
        """
        Проверяет валидность входного файла изображения.
        
        Args:
            input_file: Входной файл для проверки
            
        Returns:
            bool: True если файл валиден, False иначе
        """
        try:
            # Получаем расширение файла
            if hasattr(input_file, 'name'):
                filename = input_file.name
            else:
                filename = str(input_file)
            
            if not filename:
                return False
            
            file_extension = Path(filename).suffix.lower().lstrip('.')
            return file_extension in self.SUPPORTED_INPUT_FORMATS
            
        except Exception as e:
            self.logger.warning(f"Ошибка при валидации входного файла: {e}")
            return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """
        Проверяет доступность зависимостей для конвертации изображений.
        
        Returns:
            dict: Статус доступности зависимостей
        """
        dependencies = super().check_dependencies()
        
        # Проверяем PIL/Pillow
        try:
            from PIL import Image
            dependencies['pillow'] = True
        except ImportError:
            dependencies['pillow'] = False
        
        # Проверяем OpenCV
        try:
            import cv2
            dependencies['opencv'] = True
        except ImportError:
            dependencies['opencv'] = False
        
        return dependencies
    
    def is_available(self) -> bool:
        """
        Проверяет доступность хотя бы одного движка конвертации.
        
        Returns:
            bool: True если хотя бы один движок доступен
        """
        deps = self.check_dependencies()
        return deps.get('pillow', False) or deps.get('opencv', False)

    def _create_animated_gif(self, image, output_path, **kwargs) -> ConversionResult:
        """
        Создает анимированный GIF из статичного изображения с эффектами.

        Args:
            image (PIL.Image): Исходное изображение.
            output_path (str): Путь для сохранения GIF.
            **kwargs: Параметры для создания GIF.

        Returns:
            ConversionResult: Результат создания GIF.
        """
        from PIL import Image, ImageEnhance

        try:
            duration = int(kwargs.get('gif_duration', 200))
            loop = int(kwargs.get('gif_loop', 0))
            frames_count = int(kwargs.get('gif_frames', 10))
            effect = kwargs.get('gif_effect', 'none')

            # Гарантируем, что изображение в режиме RGBA для работы с прозрачностью
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            frames = []
            if effect == 'fade':
                frames = self._effect_fade(image, frames_count)
            elif effect == 'zoom':
                frames = self._effect_zoom(image, frames_count)
            elif effect == 'rotate':
                frames = self._effect_rotate(image, frames_count)
            elif effect == 'bounce':
                frames = self._effect_bounce(image, frames_count)
            else:  # none
                frames = [image.copy() for _ in range(frames_count)]

            if not frames:
                return ConversionResult(success=False, error_message="Не удалось создать кадры для GIF.")

            # Сохраняем как анимированный GIF
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=loop,
                optimize=True,
                format='GIF',
                transparency=0,  # Устанавливаем прозрачность
                disposal=2       # Правильное перекрытие кадров
            )
            
            metadata = {
                'animation_frames': len(frames),
                'animation_duration_ms': duration * len(frames),
                'animation_effect': effect
            }

            return ConversionResult(success=True, output_path=str(output_path), metadata=metadata)

        except Exception as e:
            self.logger.error(f"Ошибка при создании GIF: {e}")
            return ConversionResult(success=False, error_message=str(e))

    def _effect_fade(self, image, frames_count):
        frames = []
        for i in range(frames_count):
            alpha = int(255 * (i / (frames_count - 1)))
            temp_img = image.copy()
            temp_img.putalpha(alpha)
            frames.append(temp_img)
        return frames + frames[::-1]  # Fade in and out

    def _effect_zoom(self, image, frames_count):
        frames = []
        w, h = image.size
        for i in range(frames_count):
            scale = 1 + 0.5 * (i / (frames_count - 1))
            new_size = (int(w * scale), int(h * scale))
            zoomed_img = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Обрезка до оригинального размера
            left = (zoomed_img.width - w) / 2
            top = (zoomed_img.height - h) / 2
            right = (zoomed_img.width + w) / 2
            bottom = (zoomed_img.height + h) / 2
            
            cropped = zoomed_img.crop((left, top, right, bottom))
            frames.append(cropped)
        return frames

    def _effect_rotate(self, image, frames_count):
        frames = []
        for i in range(frames_count):
            angle = 360 * (i / frames_count)
            # expand=True чтобы избежать обрезки
            rotated_img = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
            
            # Создаем фон и вставляем изображение, чтобы сохранить размер
            background = Image.new('RGBA', (rotated_img.width, rotated_img.height), (255, 255, 255, 0))
            background.paste(rotated_img, (0, 0), rotated_img)
            
            # Масштабируем до оригинального размера
            final_frame = background.resize(image.size, Image.Resampling.LANCZOS)
            frames.append(final_frame)
        return frames

    def _effect_bounce(self, image, frames_count):
        import math
        frames = []
        w, h = image.size
        for i in range(frames_count):
            # Простое движение вверх-вниз
            offset = int(15 * math.sin(2 * math.pi * i / frames_count))
            frame = Image.new('RGBA', image.size, (255, 255, 255, 0))
            frame.paste(image, (0, offset))
            frames.append(frame)
        return frames
