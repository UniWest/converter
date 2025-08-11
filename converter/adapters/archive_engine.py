"""
Адаптер для работы с архивными файлами.
Базовая реализация с возможностью расширения.
"""

import os
from pathlib import Path
from typing import Any, Dict, Union

from .base import BaseEngine, ConversionResult, EngineNotAvailableError, ConversionError, UnsupportedFormatError


class ArchiveEngine(BaseEngine):
    """
    Адаптер для работы с архивными файлами.
    Базовая реализация для будущего расширения функциональности.
    """
    
    # Поддерживаемые форматы
    SUPPORTED_INPUT_FORMATS = [
        'zip', 'rar', '7z', 'tar', 'tar.gz', 'tgz', 'tar.bz2', 'tbz2',
        'tar.xz', 'txz', 'gz', 'bz2', 'xz', 'lzma', 'lz4', 'zst',
        'cab', 'arj', 'lzh', 'ace', 'iso', 'dmg'
    ]
    
    SUPPORTED_OUTPUT_FORMATS = [
        'zip', '7z', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz'
    ]
    
    def __init__(self, **config):
        """
        Инициализация адаптера архивов.
        
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
        Конвертирует архив (изменяет формат архивации).
        
        Args:
            input_file: Входной архивный файл
            output_path: Путь для сохранения результата
            **kwargs: Параметры конвертации:
                - compression_level: Уровень сжатия (0-9)
                - password: Пароль для защищенного архива
                - extract_to: Временная папка для распаковки
                - include_files: Список файлов для включения
                - exclude_files: Список файлов для исключения
                - preserve_structure: Сохранить структуру каталогов
                - method: Метод сжатия ('deflate', 'bzip2', 'lzma')
                
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
            output_name = Path(output_path).name.lower()
            output_format = None
            
            # Проверяем составные расширения
            for fmt in ['tar.gz', 'tar.bz2', 'tar.xz']:
                if output_name.endswith(fmt):
                    output_format = fmt
                    break
            
            if not output_format:
                output_format = Path(output_path).suffix.lower().lstrip('.')
            
            if output_format not in self.SUPPORTED_OUTPUT_FORMATS:
                return ConversionResult(
                    success=False,
                    error_message=f"Неподдерживаемый формат выходного файла: {output_format}"
                )
            
            # Пока возвращаем заглушку - в будущем можно добавить zipfile/tarfile/py7zr
            return ConversionResult(
                success=False,
                error_message="Конвертация архивов пока не реализована"
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при конвертации архива: {e}")
            return ConversionResult(
                success=False,
                error_message=f"Произошла ошибка: {str(e)}"
            )
    
    def extract(
        self,
        input_file: Union[str, Path, Any],
        extract_path: Union[str, Path],
        **kwargs
    ) -> ConversionResult:
        """
        Извлекает содержимое архива.
        
        Args:
            input_file: Входной архивный файл
            extract_path: Путь для извлечения файлов
            **kwargs: Дополнительные параметры извлечения
            
        Returns:
            ConversionResult: Результат извлечения
        """
        try:
            if not self.validate_input(input_file):
                return ConversionResult(
                    success=False,
                    error_message="Неподдерживаемый формат архива"
                )
            
            # Пока возвращаем заглушку
            return ConversionResult(
                success=False,
                error_message="Извлечение архивов пока не реализовано"
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении архива: {e}")
            return ConversionResult(
                success=False,
                error_message=f"Произошла ошибка: {str(e)}"
            )
    
    def create_archive(
        self,
        source_paths: list,
        output_path: Union[str, Path],
        **kwargs
    ) -> ConversionResult:
        """
        Создает архив из файлов и папок.
        
        Args:
            source_paths: Список путей к файлам и папкам для архивации
            output_path: Путь для сохранения архива
            **kwargs: Дополнительные параметры архивации
            
        Returns:
            ConversionResult: Результат создания архива
        """
        try:
            # Пока возвращаем заглушку
            return ConversionResult(
                success=False,
                error_message="Создание архивов пока не реализовано"
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании архива: {e}")
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
        Проверяет валидность входного архивного файла.
        
        Args:
            input_file: Входной файл для проверки
            
        Returns:
            bool: True если файл валиден, False иначе
        """
        try:
            # Получаем имя файла
            if hasattr(input_file, 'name'):
                filename = input_file.name
            else:
                filename = str(input_file)
            
            if not filename:
                return False
            
            filename_lower = filename.lower()
            
            # Проверяем составные расширения
            for fmt in ['tar.gz', 'tar.bz2', 'tar.xz']:
                if filename_lower.endswith(fmt):
                    return fmt in self.SUPPORTED_INPUT_FORMATS
            
            # Проверяем простые расширения
            file_extension = Path(filename).suffix.lower().lstrip('.')
            return file_extension in self.SUPPORTED_INPUT_FORMATS
            
        except Exception as e:
            self.logger.warning(f"Ошибка при валидации входного файла: {e}")
            return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """
        Проверяет доступность зависимостей для работы с архивами.
        
        Returns:
            dict: Статус доступности зависимостей
        """
        dependencies = super().check_dependencies()
        
        # Встроенные модули Python
        try:
            import zipfile
            dependencies['zipfile'] = True
        except ImportError:
            dependencies['zipfile'] = False
        
        try:
            import tarfile
            dependencies['tarfile'] = True
        except ImportError:
            dependencies['tarfile'] = False
        
        try:
            import gzip
            dependencies['gzip'] = True
        except ImportError:
            dependencies['gzip'] = False
        
        try:
            import bz2
            dependencies['bz2'] = True
        except ImportError:
            dependencies['bz2'] = False
        
        try:
            import lzma
            dependencies['lzma'] = True
        except ImportError:
            dependencies['lzma'] = False
        
        # Внешние библиотеки
        try:
            import py7zr
            dependencies['py7zr'] = True
        except ImportError:
            dependencies['py7zr'] = False
        
        try:
            import rarfile
            dependencies['rarfile'] = True
        except ImportError:
            dependencies['rarfile'] = False
        
        return dependencies
    
    def is_available(self) -> bool:
        """
        Проверяет доступность хотя бы одного движка для работы с архивами.
        
        Returns:
            bool: True если хотя бы один движок доступен
        """
        deps = self.check_dependencies()
        return (deps.get('zipfile', False) or 
                deps.get('tarfile', False) or
                deps.get('py7zr', False) or
                deps.get('rarfile', False))
