"""
Базовые классы и интерфейсы для адаптеров конвертеров файлов.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """
    Результат конвертации файла.
    
    Attributes:
        success: Успешность выполнения операции
        output_path: Путь к конвертированному файлу
        error_message: Сообщение об ошибке (если есть)
        metadata: Дополнительные метаданные о результате
    """
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseEngine(ABC):
    """
    Базовый абстрактный класс для всех адаптеров конвертеров.
    
    Определяет общий интерфейс, который должны реализовать все конкретные адаптеры.
    """
    
    def __init__(self, **config):
        """
        Инициализация базового адаптера.
        
        Args:
            **config: Конфигурационные параметры для адаптера
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def convert(
        self, 
        input_file: Union[str, Path, Any], 
        output_path: Union[str, Path],
        **kwargs
    ) -> ConversionResult:
        """
        Основной метод конвертации файла.
        
        Args:
            input_file: Входной файл для конвертации
            output_path: Путь для сохранения результата
            **kwargs: Дополнительные параметры конвертации
            
        Returns:
            ConversionResult: Результат операции конвертации
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> Dict[str, list]:
        """
        Возвращает поддерживаемые форматы входных и выходных файлов.
        
        Returns:
            dict: Словарь с ключами 'input' и 'output', содержащими списки форматов
        """
        pass
    
    @abstractmethod
    def validate_input(self, input_file: Union[str, Path, Any]) -> bool:
        """
        Проверяет валидность входного файла.
        
        Args:
            input_file: Входной файл для проверки
            
        Returns:
            bool: True если файл валиден, False иначе
        """
        pass
    
    def get_file_info(self, input_file: Union[str, Path, Any]) -> Dict[str, Any]:
        """
        Получает информацию о файле.
        
        Args:
            input_file: Файл для анализа
            
        Returns:
            dict: Информация о файле
        """
        try:
            if hasattr(input_file, 'size'):
                # Django UploadedFile
                return {
                    'name': input_file.name,
                    'size': input_file.size,
                    'content_type': getattr(input_file, 'content_type', 'unknown')
                }
            else:
                # Путь к файлу
                file_path = Path(input_file)
                if file_path.exists():
                    return {
                        'name': file_path.name,
                        'size': file_path.stat().st_size,
                        'content_type': 'unknown'
                    }
        except Exception as e:
            self.logger.warning(f"Не удалось получить информацию о файле: {e}")
        
        return {}
    
    def check_dependencies(self) -> Dict[str, bool]:
        """
        Проверяет доступность необходимых зависимостей.
        
        Returns:
            dict: Статус доступности зависимостей
        """
        return {'base': True}
    
    def cleanup_temp_files(self, file_paths: list):
        """
        Очищает временные файлы.
        
        Args:
            file_paths: Список путей к файлам для удаления
        """
        import os
        
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Удален временный файл: {file_path}")
            except Exception as e:
                self.logger.warning(f"Не удалось удалить временный файл {file_path}: {e}")


class EngineNotAvailableError(Exception):
    """Исключение для случаев, когда движок конвертации недоступен."""
    pass


class ConversionError(Exception):
    """Исключение для ошибок конвертации."""
    pass


class UnsupportedFormatError(Exception):
    """Исключение для неподдерживаемых форматов файлов."""
    pass
