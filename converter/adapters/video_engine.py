from .base import BaseEngine, ConversionResult
"""
Адаптер для конвертации видео файлов.
Использует существующую логику VideoConverter.
"""

import os
from pathlib import Path
from typing import Any, Dict, Union

from ..utils import VideoConverter


class VideoEngine(BaseEngine):
    """
    Адаптер для конвертации видео файлов.
    Обертка над существующим VideoConverter.
    """
    
    # Поддерживаемые форматы
    SUPPORTED_INPUT_FORMATS = [
        'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'm4v', 
        'wmv', 'mpg', 'mpeg', '3gp', 'ogg', 'ogv'
    ]
    
    SUPPORTED_OUTPUT_FORMATS = [
        'gif', 'mp4', 'webm', 'avi'
    ]
    
    def __init__(self, use_moviepy: bool = True, **config):
        """
        Инициализация адаптера видео конвертера.
        
        Args:
            use_moviepy: Использовать MoviePy вместо FFmpeg
            **config: Дополнительные параметры конфигурации
        """
        super().__init__(**config)
        self.use_moviepy = use_moviepy
        self._video_converter = None
    
    @property
    def video_converter(self) -> VideoConverter:
        """Ленивая инициализация VideoConverter."""
        if self._video_converter is None:
            self._video_converter = VideoConverter(use_moviepy=self.use_moviepy)
        return self._video_converter
    
    def convert(
        self, 
        input_file: Union[str, Path, Any], 
        output_path: Union[str, Path],
        **kwargs
    ) -> ConversionResult:
        """
        Конвертирует видео файл.
        
        Args:
            input_file: Входной видео файл
            output_path: Путь для сохранения результата
            **kwargs: Параметры конвертации:
                - width: Ширина выходного файла
                - fps: Частота кадров
                - start_time: Начальное время
                - end_time: Конечное время
                - keep_original_size: Сохранить оригинальный размер
                - speed: Скорость воспроизведения
                - grayscale: Черно-белое изображение
                - reverse: Обратное воспроизведение
                - boomerang: Эффект бумеранга
                - high_quality: Высокое качество
                - dither: Тип дизеринга
                
        Returns:
            ConversionResult: Результат конвертации
        """
        temp_files = []
        
        try:
            # Валидация входного файла
            if not self.validate_input(input_file):
                return ConversionResult(
                    success=False,
                    error_message="Неподдерживаемый формат входного файла"
                )
            
            # Определяем выходной формат по расширению
            output_format = Path(output_path).suffix.lower().lstrip('.')
            if output_format not in self.SUPPORTED_OUTPUT_FORMATS:
                return ConversionResult(
                    success=False,
                    error_message=f"Неподдерживаемый формат выходного файла: {output_format}"
                )
            
            # Получаем информацию о входном файле
            input_info = self.get_file_info(input_file)
            
            # Для GIF используем существующую логику VideoConverter
            if output_format == 'gif':
                success = self.video_converter.convert_video_to_gif(
                    input_file, str(output_path), **kwargs
                )
                
                if success and os.path.exists(output_path):
                    output_info = {
                        'format': 'gif',
                        'size': os.path.getsize(output_path)
                    }
                    
                    return ConversionResult(
                        success=True,
                        output_path=str(output_path),
                        metadata={
                            'input_info': input_info,
                            'output_info': output_info,
                            'conversion_params': kwargs
                        }
                    )
                else:
                    return ConversionResult(
                        success=False,
                        error_message="Ошибка при конвертации в GIF"
                    )
            
            # Для других форматов пока возвращаем ошибку
            # В будущем можно добавить поддержку других форматов
            else:
                return ConversionResult(
                    success=False,
                    error_message=f"Конвертация в формат {output_format} пока не поддерживается"
                )
                
        except Exception as e:
            self.logger.error(f"Ошибка при конвертации видео: {e}")
            return ConversionResult(
                success=False,
                error_message=f"Произошла ошибка: {str(e)}"
            )
        
        finally:
            # Очищаем временные файлы
            self.cleanup_temp_files(temp_files)
    
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
        Проверяет валидность входного видео файла.
        
        Args:
            input_file: Входной файл для проверки
            
        Returns:
            bool: True если файл валиден, False иначе
        """
        try:
            # Получаем расширение файла
            if hasattr(input_file, 'name'):
                # Django UploadedFile
                filename = input_file.name
            else:
                # Путь к файлу
                filename = str(input_file)
            
            if not filename:
                return False
            
            file_extension = Path(filename).suffix.lower().lstrip('.')
            return file_extension in self.SUPPORTED_INPUT_FORMATS
            
        except Exception as e:
            self.logger.warning(f"Ошибка при валидации входного файла: {e}")
            return False
    
    def get_video_info(self, input_file: Union[str, Path, Any]) -> Dict[str, Any]:
        """
        Получает детальную информацию о видео файле.
        
        Args:
            input_file: Видео файл для анализа
            
        Returns:
            dict: Информация о видео файле
        """
        try:
            video_info = self.video_converter.get_video_info(input_file)
            
            # Дополняем базовую информацию о файле
            base_info = self.get_file_info(input_file)
            
            return {
                **base_info,
                **video_info
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации о видео: {e}")
            return self.get_file_info(input_file)
    
    def check_dependencies(self) -> Dict[str, bool]:
        """
        Проверяет доступность зависимостей для видео конвертации.
        
        Returns:
            dict: Статус доступности зависимостей
        """
        dependencies = super().check_dependencies()
        
        # Проверяем MoviePy
        
        # Проверяем FFmpeg через VideoConverter
        try:
            from django.conf import settings
            ffmpeg_path = getattr(settings, 'FFMPEG_BINARY', 'ffmpeg')
            dependencies['ffmpeg'] = self.video_converter._check_ffmpeg(ffmpeg_path)
            dependencies['ffmpeg_path'] = ffmpeg_path
        except Exception:
            dependencies['ffmpeg'] = False
            dependencies['ffmpeg_path'] = 'unknown'
        
        return dependencies
    
    def set_moviepy_mode(self, use_moviepy: bool):
        """
        Переключает режим использования MoviePy/FFmpeg.
        
        Args:
            use_moviepy: True для MoviePy, False для FFmpeg
        """
        self.use_moviepy = use_moviepy
        self._video_converter = None  # Сброс для пересоздания с новыми настройками
    
    def is_available(self) -> bool:
        """
        Проверяет доступность хотя бы одного движка конвертации.
        
        Returns:
            bool: True если хотя бы один движок доступен
        """
        deps = self.check_dependencies()
        return deps.get('moviepy', False) or deps.get('ffmpeg', False)
