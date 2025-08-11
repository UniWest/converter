"""
Менеджер адаптеров для централизованного управления конвертерами.
"""

from typing import Dict, Optional, Type, Union
from pathlib import Path
import logging

from .base import BaseEngine, ConversionResult
from .video_engine import VideoEngine
from .image_engine import ImageEngine
from .audio_engine import AudioEngine
from .document_engine import DocumentEngine
from .archive_engine import ArchiveEngine

logger = logging.getLogger(__name__)


class EngineManager:
    """
    Менеджер для управления различными адаптерами конвертеров.
    
    Обеспечивает единую точку доступа ко всем типам конвертеров и
    автоматическое определение подходящего адаптера по типу файла.
    """
    
    def __init__(self):
        """Инициализация менеджера адаптеров."""
        self._engines: Dict[str, BaseEngine] = {}
        self._engine_classes: Dict[str, Type[BaseEngine]] = {
            'video': VideoEngine,
            'image': ImageEngine,
            'audio': AudioEngine,
            'document': DocumentEngine,
            'archive': ArchiveEngine,
        }
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def get_engine(self, engine_type: str, **config) -> Optional[BaseEngine]:
        """
        Получает адаптер указанного типа.
        
        Args:
            engine_type: Тип адаптера ('video', 'image', 'audio', 'document', 'archive')
            **config: Конфигурационные параметры для адаптера
            
        Returns:
            BaseEngine: Экземпляр адаптера или None если тип не поддерживается
        """
        try:
            if engine_type not in self._engine_classes:
                self.logger.error(f"Неподдерживаемый тип адаптера: {engine_type}")
                return None
            
            # Создаем ключ для кэширования с учетом конфигурации
            cache_key = f"{engine_type}_{hash(str(sorted(config.items())))}"
            
            if cache_key not in self._engines:
                engine_class = self._engine_classes[engine_type]
                self._engines[cache_key] = engine_class(**config)
                self.logger.debug(f"Создан новый адаптер: {engine_type}")
            
            return self._engines[cache_key]
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании адаптера {engine_type}: {e}")
            return None
    
    def detect_engine_type(self, filename: str) -> Optional[str]:
        """
        Определяет тип адаптера по имени файла.
        
        Args:
            filename: Имя файла
            
        Returns:
            str: Тип адаптера или None если тип не определен
        """
        try:
            if not filename:
                return None
            
            filename_lower = filename.lower()
            
            # Сначала проверяем составные расширения для архивов
            archive_extensions = ['tar.gz', 'tar.bz2', 'tar.xz']
            for ext in archive_extensions:
                if filename_lower.endswith(ext):
                    return 'archive'
            
            # Затем проверяем простые расширения
            file_extension = Path(filename).suffix.lower().lstrip('.')
            
            # Определяем тип по расширению
            extension_mapping = {
                # Видео
                'mp4': 'video', 'avi': 'video', 'mov': 'video', 'mkv': 'video',
                'webm': 'video', 'flv': 'video', 'm4v': 'video', 'wmv': 'video',
                'mpg': 'video', 'mpeg': 'video', '3gp': 'video', 'ogg': 'video',
                'ogv': 'video', 'gif': 'video',  # GIF как видео для конвертации
                
                # Изображения  
                'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'bmp': 'image',
                'tiff': 'image', 'tif': 'image', 'webp': 'image', 'svg': 'image',
                'ico': 'image', 'psd': 'image', 'raw': 'image', 'heic': 'image',
                'heif': 'image',
                
                # Аудио
                'mp3': 'audio', 'wav': 'audio', 'flac': 'audio', 'aac': 'audio',
                'm4a': 'audio', 'wma': 'audio', 'opus': 'audio', 'amr': 'audio',
                'ra': 'audio', 'au': 'audio', 'aiff': 'audio', 'caf': 'audio',
                
                # Документы
                'pdf': 'document', 'doc': 'document', 'docx': 'document',
                'rtf': 'document', 'odt': 'document', 'txt': 'document',
                'md': 'document', 'html': 'document', 'htm': 'document',
                'xls': 'document', 'xlsx': 'document', 'ods': 'document',
                'csv': 'document', 'ppt': 'document', 'pptx': 'document',
                'odp': 'document', 'epub': 'document', 'mobi': 'document',
                'fb2': 'document', 'djvu': 'document', 'tex': 'document',
                'latex': 'document',
                
                # Архивы
                'zip': 'archive', 'rar': 'archive', '7z': 'archive',
                'tar': 'archive', 'gz': 'archive', 'bz2': 'archive',
                'xz': 'archive', 'lzma': 'archive', 'lz4': 'archive',
                'zst': 'archive', 'cab': 'archive', 'arj': 'archive',
                'lzh': 'archive', 'ace': 'archive', 'iso': 'archive',
                'dmg': 'archive',
            }
            
            return extension_mapping.get(file_extension)
            
        except Exception as e:
            self.logger.warning(f"Ошибка при определении типа файла {filename}: {e}")
            return None
    
    def convert_file(
        self,
        input_file: Union[str, Path, any],
        output_path: Union[str, Path],
        engine_type: Optional[str] = None,
        **kwargs
    ) -> ConversionResult:
        """
        Конвертирует файл, автоматически выбирая подходящий адаптер.
        
        Args:
            input_file: Входной файл
            output_path: Путь для сохранения результата
            engine_type: Тип адаптера (если не указан, определяется автоматически)
            **kwargs: Параметры конвертации
            
        Returns:
            ConversionResult: Результат конвертации
        """
        try:
            # Определяем тип адаптера
            if engine_type is None:
                # Получаем имя файла
                if hasattr(input_file, 'name'):
                    filename = input_file.name
                else:
                    filename = str(input_file)
                
                engine_type = self.detect_engine_type(filename)
                
                if engine_type is None:
                    return ConversionResult(
                        success=False,
                        error_message="Не удалось определить тип файла для конвертации"
                    )
            
            # Получаем адаптер
            engine = self.get_engine(engine_type, **kwargs.get('engine_config', {}))
            
            if engine is None:
                return ConversionResult(
                    success=False,
                    error_message=f"Адаптер типа '{engine_type}' недоступен"
                )
            
            # Проверяем доступность адаптера
            if not engine.is_available():
                deps = engine.check_dependencies()
                missing_deps = [k for k, v in deps.items() if not v]
                return ConversionResult(
                    success=False,
                    error_message=f"Адаптер '{engine_type}' недоступен. "
                                f"Отсутствуют зависимости: {missing_deps}"
                )
            
            # Выполняем конвертацию
            return engine.convert(input_file, output_path, **kwargs)
            
        except Exception as e:
            self.logger.error(f"Ошибка при конвертации файла: {e}")
            return ConversionResult(
                success=False,
                error_message=f"Произошла ошибка: {str(e)}"
            )
    
    def get_supported_formats(self, engine_type: Optional[str] = None) -> Dict[str, Dict[str, list]]:
        """
        Возвращает поддерживаемые форматы для указанного типа или всех типов.
        
        Args:
            engine_type: Тип адаптера (если не указан, возвращает все)
            
        Returns:
            dict: Словарь с поддерживаемыми форматами
        """
        try:
            if engine_type:
                engine = self.get_engine(engine_type)
                if engine:
                    return {engine_type: engine.get_supported_formats()}
                return {}
            
            # Возвращаем форматы для всех адаптеров
            all_formats = {}
            for engine_type in self._engine_classes.keys():
                engine = self.get_engine(engine_type)
                if engine:
                    all_formats[engine_type] = engine.get_supported_formats()
            
            return all_formats
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка форматов: {e}")
            return {}
    
    def get_engine_status(self) -> Dict[str, Dict[str, any]]:
        """
        Возвращает статус всех адаптеров.
        
        Returns:
            dict: Информация о статусе каждого адаптера
        """
        try:
            status = {}
            
            for engine_type in self._engine_classes.keys():
                engine = self.get_engine(engine_type)
                if engine:
                    dependencies = engine.check_dependencies()
                    status[engine_type] = {
                        'available': engine.is_available(),
                        'dependencies': dependencies,
                        'supported_formats': engine.get_supported_formats()
                    }
                else:
                    status[engine_type] = {
                        'available': False,
                        'dependencies': {},
                        'supported_formats': {'input': [], 'output': []}
                    }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении статуса адаптеров: {e}")
            return {}
    
    def clear_cache(self):
        """Очищает кэш созданных адаптеров."""
        self._engines.clear()
        self.logger.debug("Кэш адаптеров очищен")


# Глобальный экземпляр менеджера
engine_manager = EngineManager()
