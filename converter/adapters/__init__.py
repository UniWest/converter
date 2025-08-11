"""
Пакет адаптеров для различных типов конвертеров файлов.
"""

from .base import BaseEngine, ConversionResult
from .video_engine import VideoEngine
from .image_engine import ImageEngine
from .audio_engine import AudioEngine
from .document_engine import DocumentEngine
from .archive_engine import ArchiveEngine
from .engine_manager import EngineManager, engine_manager

__all__ = [
    'BaseEngine',
    'ConversionResult',
    'VideoEngine',
    'ImageEngine',
    'AudioEngine',
    'DocumentEngine',
    'ArchiveEngine',
    'EngineManager',
    'engine_manager',
]
