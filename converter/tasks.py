# -*- coding: utf-8 -*-
"""
Celery задачи для асинхронной конвертации файлов
Включает обработку видео, аудио, изображений, документов и архивов
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from celery import shared_task, current_task
from django.conf import settings
from django.utils import timezone

from .models import ConversionTask
from .adapters.engine_manager import EngineManager
from converter_settings import TEMP_DIRS

# Настройка логирования
logger = logging.getLogger(__name__)


def create_temp_directories():
    """Создание временных директорий если они не существуют"""
    for temp_type, temp_path in TEMP_DIRS.items():
        full_path = Path(settings.MEDIA_ROOT) / temp_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f'Создана временная директория: {full_path}')


def update_task_progress(task_id: str, progress: int, message: str = ""):
    """
    Обновление прогресса задачи
    
    Args:
        task_id: ID задачи
        progress: Прогресс от 0 до 100
        message: Дополнительное сообщение
    """
    try:
        task = ConversionTask.objects.get(id=task_id)
        task.update_progress(progress)
        
        if message:
            metadata = task.task_metadata or {}
            metadata['last_message'] = message
            metadata['last_updated'] = timezone.now().isoformat()
            task.task_metadata = metadata
            task.save(update_fields=['task_metadata'])
        
        logger.info(f'Задача {task_id}: прогресс {progress}% - {message}')
        
        # Обновляем статус Celery задачи
        if current_task:
            current_task.update_state(
                state='PROGRESS',
                meta={'progress': progress, 'message': message}
            )
            
    except ConversionTask.DoesNotExist:
        logger.warning(f'Задача {task_id} не найдена в базе данных')
    except Exception as e:
        logger.error(f'Ошибка обновления прогресса задачи {task_id}: {e}')


def cleanup_files(*file_paths):
    """
    Очистка временных файлов
    
    Args:
        *file_paths: Пути к файлам для удаления
    """
    for file_path in file_paths:
        try:
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
                logger.debug(f'Удален временный файл: {file_path}')
        except Exception as e:
            logger.warning(f'Не удалось удалить файл {file_path}: {e}')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def convert_video(self, task_id: str, input_path: str, output_format: str, 
                  quality: str = 'medium', custom_options: Optional[Dict[str, Any]] = None):
    """
    Конвертация видео файлов
    
    Args:
        task_id: ID задачи конвертации
        input_path: Путь к входному файлу
        output_format: Формат выхода
        quality: Качество конвертации (high, medium, low)
        custom_options: Дополнительные опции конвертации
    """
    temp_files = []
    
    try:
        create_temp_directories()
        update_task_progress(task_id, 5, "Инициализация конвертации видео")
        
        # Получение задачи из базы данных
        conversion_task = ConversionTask.objects.get(id=task_id)
        
        # Создание менеджера движков
        engine_manager = EngineManager()
        update_task_progress(task_id, 10, "Подготовка движка конвертации")
        
        # Подготовка выходного файла
        input_file = Path(input_path)
        output_dir = Path(settings.MEDIA_ROOT) / TEMP_DIRS['output']
        output_file = output_dir / f"{input_file.stem}_{int(time.time())}.{output_format}"
        temp_files.append(str(output_file))
        
        update_task_progress(task_id, 20, "Начало конвертации видео")
        
        # Выполнение конвертации
        def progress_callback(percent):
            # Прогресс конвертации занимает 20-90%
            actual_progress = 20 + int(percent * 0.7)
            update_task_progress(task_id, actual_progress, f"Конвертация: {percent:.1f}%")
        
        result = engine_manager.get_engine('video').convert(
            input_path=str(input_file),
            output_path=str(output_file),
            output_format=output_format,
            quality=quality,
            custom_options=custom_options or {},
            progress_callback=progress_callback
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Ошибка конвертации видео'))
        
        update_task_progress(task_id, 95, "Финализация результата")
        
        # Сохранение метаданных результата
        conversion_task.set_metadata(
            output_file=str(output_file),
            output_format=output_format,
            quality=quality,
            file_size=output_file.stat().st_size if output_file.exists() else 0,
            conversion_time=result.get('duration', 0),
            engine_info=result.get('engine_info', {})
        )
        conversion_task.save()
        
        update_task_progress(task_id, 100, "Конвертация видео завершена")
        
        return {
            'success': True,
            'output_file': str(output_file),
            'metadata': result
        }
        
    except Exception as exc:
        logger.error(f'Ошибка в задаче convert_video {task_id}: {exc}')
        
        # Очистка временных файлов при ошибке
        cleanup_files(*temp_files)
        
        # Обновление статуса задачи
        try:
            conversion_task = ConversionTask.objects.get(id=task_id)
            conversion_task.fail(str(exc))
        except:
            pass
        
        # Повторная попытка при возможности
        if self.request.retries < self.max_retries:
            logger.info(f'Повторная попытка конвертации видео {task_id} через {self.default_retry_delay} секунд')
            raise self.retry(exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def convert_video_to_gif_hardened(self, task_id: int, input_path: str, **conversion_options):
    """
    Hardened video to GIF conversion task with advanced FFmpeg backend.
    
    Args:
        task_id: ConversionTask ID for progress tracking
        input_path: Path to input video file  
        **conversion_options: All conversion parameters from VideoUploadForm
    """
    from .services import VideoConversionService
    
    try:
        update_task_progress(task_id, 5, "Запуск защищённой конвертации видео в GIF")
        
        # Initialize conversion service
        conversion_service = VideoConversionService()
        
        # Perform conversion
        result = conversion_service.convert_video_to_gif(
            task_id=task_id,
            input_path=input_path,
            **conversion_options
        )
        
        if result['success']:
            update_task_progress(task_id, 100, "Конвертация успешно завершена")
            return result
        else:
            # Task failure is already handled in the service
            raise Exception(result.get('error_message', 'Неизвестная ошибка конвертации'))
            
    except Exception as exc:
        logger.error(f'Ошибка в задаче convert_video_to_gif_hardened {task_id}: {exc}')
        
        # Update task status
        try:
            conversion_task = ConversionTask.objects.get(id=task_id)
            conversion_task.fail(str(exc))
        except:
            pass
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f'Повторная попытка конвертации GIF {task_id} через {self.default_retry_delay} секунд')
            raise self.retry(exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def convert_audio(self, task_id: str, input_path: str, output_format: str,
                  quality: str = 'medium', custom_options: Optional[Dict[str, Any]] = None):
    """
    Конвертация аудио файлов
    
    Args:
        task_id: ID задачи конвертации
        input_path: Путь к входному файлу
        output_format: Формат выхода
        quality: Качество конвертации
        custom_options: Дополнительные опции
    """
    temp_files = []
    
    try:
        create_temp_directories()
        update_task_progress(task_id, 10, "Инициализация конвертации аудио")
        
        conversion_task = ConversionTask.objects.get(id=task_id)
        engine_manager = EngineManager()
        
        input_file = Path(input_path)
        output_dir = Path(settings.MEDIA_ROOT) / TEMP_DIRS['output']
        output_file = output_dir / f"{input_file.stem}_{int(time.time())}.{output_format}"
        temp_files.append(str(output_file))
        
        update_task_progress(task_id, 25, "Начало конвертации аудио")
        
        def progress_callback(percent):
            actual_progress = 25 + int(percent * 0.65)
            update_task_progress(task_id, actual_progress, f"Конвертация: {percent:.1f}%")
        
        result = engine_manager.get_engine('audio').convert(
            input_path=str(input_file),
            output_path=str(output_file),
            output_format=output_format,
            quality=quality,
            custom_options=custom_options or {},
            progress_callback=progress_callback
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Ошибка конвертации аудио'))
        
        update_task_progress(task_id, 95, "Финализация результата")
        
        conversion_task.set_metadata(
            output_file=str(output_file),
            output_format=output_format,
            quality=quality,
            file_size=output_file.stat().st_size if output_file.exists() else 0,
            conversion_time=result.get('duration', 0)
        )
        conversion_task.save()
        
        update_task_progress(task_id, 100, "Конвертация аудио завершена")
        
        return {
            'success': True,
            'output_file': str(output_file),
            'metadata': result
        }
        
    except Exception as exc:
        logger.error(f'Ошибка в задаче convert_audio {task_id}: {exc}')
        cleanup_files(*temp_files)
        
        try:
            conversion_task = ConversionTask.objects.get(id=task_id)
            conversion_task.fail(str(exc))
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def convert_image(self, task_id: str, input_path: str, output_format: str,
                  quality: str = 'medium', custom_options: Optional[Dict[str, Any]] = None):
    """
    Конвертация изображений
    
    Args:
        task_id: ID задачи конвертации
        input_path: Путь к входному файлу
        output_format: Формат выхода
        quality: Качество конвертации
        custom_options: Дополнительные опции (размер, сжатие и т.д.)
    """
    temp_files = []
    
    try:
        create_temp_directories()
        update_task_progress(task_id, 15, "Инициализация конвертации изображения")
        
        conversion_task = ConversionTask.objects.get(id=task_id)
        engine_manager = EngineManager()
        
        input_file = Path(input_path)
        output_dir = Path(settings.MEDIA_ROOT) / TEMP_DIRS['output']
        output_file = output_dir / f"{input_file.stem}_{int(time.time())}.{output_format}"
        temp_files.append(str(output_file))
        
        update_task_progress(task_id, 30, "Обработка изображения")
        
        def progress_callback(percent):
            actual_progress = 30 + int(percent * 0.6)
            update_task_progress(task_id, actual_progress, f"Конвертация: {percent:.1f}%")
        
        result = engine_manager.get_engine('image').convert(
            input_path=str(input_file),
            output_path=str(output_file),
            output_format=output_format,
            quality=quality,
            custom_options=custom_options or {},
            progress_callback=progress_callback
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Ошибка конвертации изображения'))
        
        update_task_progress(task_id, 95, "Финализация результата")
        
        conversion_task.set_metadata(
            output_file=str(output_file),
            output_format=output_format,
            quality=quality,
            file_size=output_file.stat().st_size if output_file.exists() else 0,
            image_info=result.get('image_info', {})
        )
        conversion_task.save()
        
        update_task_progress(task_id, 100, "Конвертация изображения завершена")
        
        return {
            'success': True,
            'output_file': str(output_file),
            'metadata': result
        }
        
    except Exception as exc:
        logger.error(f'Ошибка в задаче convert_image {task_id}: {exc}')
        cleanup_files(*temp_files)
        
        try:
            conversion_task = ConversionTask.objects.get(id=task_id)
            conversion_task.fail(str(exc))
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def convert_document(self, task_id: str, input_path: str, output_format: str,
                     custom_options: Optional[Dict[str, Any]] = None):
    """
    Конвертация документов
    
    Args:
        task_id: ID задачи конвертации
        input_path: Путь к входному файлу
        output_format: Формат выхода
        custom_options: Дополнительные опции
    """
    temp_files = []
    
    try:
        create_temp_directories()
        update_task_progress(task_id, 10, "Инициализация конвертации документа")
        
        conversion_task = ConversionTask.objects.get(id=task_id)
        engine_manager = EngineManager()
        
        input_file = Path(input_path)
        output_dir = Path(settings.MEDIA_ROOT) / TEMP_DIRS['output']
        output_file = output_dir / f"{input_file.stem}_{int(time.time())}.{output_format}"
        temp_files.append(str(output_file))
        
        update_task_progress(task_id, 25, "Конвертация документа")
        
        def progress_callback(percent):
            actual_progress = 25 + int(percent * 0.65)
            update_task_progress(task_id, actual_progress, f"Обработка: {percent:.1f}%")
        
        result = engine_manager.get_engine('document').convert(
            input_path=str(input_file),
            output_path=str(output_file),
            output_format=output_format,
            custom_options=custom_options or {},
            progress_callback=progress_callback
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Ошибка конвертации документа'))
        
        update_task_progress(task_id, 95, "Финализация результата")
        
        conversion_task.set_metadata(
            output_file=str(output_file),
            output_format=output_format,
            file_size=output_file.stat().st_size if output_file.exists() else 0,
            document_info=result.get('document_info', {})
        )
        conversion_task.save()
        
        update_task_progress(task_id, 100, "Конвертация документа завершена")
        
        return {
            'success': True,
            'output_file': str(output_file),
            'metadata': result
        }
        
    except Exception as exc:
        logger.error(f'Ошибка в задаче convert_document {task_id}: {exc}')
        cleanup_files(*temp_files)
        
        try:
            conversion_task = ConversionTask.objects.get(id=task_id)
            conversion_task.fail(str(exc))
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def convert_archive(self, task_id: str, input_path: str, output_format: str,
                    custom_options: Optional[Dict[str, Any]] = None):
    """
    Конвертация архивов
    
    Args:
        task_id: ID задачи конвертации
        input_path: Путь к входному файлу
        output_format: Формат выхода
        custom_options: Дополнительные опции (уровень сжатия и т.д.)
    """
    temp_files = []
    
    try:
        create_temp_directories()
        update_task_progress(task_id, 10, "Инициализация конвертации архива")
        
        conversion_task = ConversionTask.objects.get(id=task_id)
        engine_manager = EngineManager()
        
        input_file = Path(input_path)
        output_dir = Path(settings.MEDIA_ROOT) / TEMP_DIRS['output']
        output_file = output_dir / f"{input_file.stem}_{int(time.time())}.{output_format}"
        temp_files.append(str(output_file))
        
        update_task_progress(task_id, 20, "Конвертация архива")
        
        def progress_callback(percent):
            actual_progress = 20 + int(percent * 0.7)
            update_task_progress(task_id, actual_progress, f"Архивирование: {percent:.1f}%")
        
        result = engine_manager.get_engine('archive').convert(
            input_path=str(input_file),
            output_path=str(output_file),
            output_format=output_format,
            custom_options=custom_options or {},
            progress_callback=progress_callback
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Ошибка конвертации архива'))
        
        update_task_progress(task_id, 95, "Финализация результата")
        
        conversion_task.set_metadata(
            output_file=str(output_file),
            output_format=output_format,
            file_size=output_file.stat().st_size if output_file.exists() else 0,
            archive_info=result.get('archive_info', {})
        )
        conversion_task.save()
        
        update_task_progress(task_id, 100, "Конвертация архива завершена")
        
        return {
            'success': True,
            'output_file': str(output_file),
            'metadata': result
        }
        
    except Exception as exc:
        logger.error(f'Ошибка в задаче convert_archive {task_id}: {exc}')
        cleanup_files(*temp_files)
        
        try:
            conversion_task = ConversionTask.objects.get(id=task_id)
            conversion_task.fail(str(exc))
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        else:
            raise exc


@shared_task(bind=True)
def process_conversion_task(self, task_id):
    """
    Универсальная задача для обработки конвертации файла.
    Получает задачу по ID, выполняет конвертацию и обновляет статус.
    """
    task = None
    temp_files = []
    
    try:
        # Получаем задачу из базы данных
        task = ConversionTask.objects.get(id=task_id)
        
        # Обновляем статус на "выполняется"
        task.start_processing()
        
        # Получаем метаданные задачи
        source_format = task.get_metadata('source_format')
        target_format = task.get_metadata('target_format')
        file_path = task.get_metadata('file_path')
        original_filename = task.get_metadata('original_filename', 'unknown')
        conversion_params = task.get_metadata('conversion_params', {})
        
        logger.info(f"Начинаем обработку задачи {task_id}: {source_format} -> {target_format}")
        update_task_progress(task_id, 10, f"Конвертация {source_format} -> {target_format}")
        
        # Определяем и вызываем соответствующую задачу конвертации
        if source_format == 'video':
            result = self.retry(
                convert_video.s(
                    task_id, file_path, target_format, 
                    conversion_params.get('quality', 'medium'), 
                    conversion_params
                )
            )
        elif source_format == 'audio':
            result = self.retry(
                convert_audio.s(
                    task_id, file_path, target_format,
                    conversion_params.get('quality', 'medium'), 
                    conversion_params
                )
            )
        elif source_format == 'image':
            result = self.retry(
                convert_image.s(
                    task_id, file_path, target_format,
                    conversion_params.get('quality', 'medium'), 
                    conversion_params
                )
            )
        elif source_format == 'document':
            result = self.retry(
                convert_document.s(
                    task_id, file_path, target_format, conversion_params
                )
            )
        elif source_format == 'archive':
            result = self.retry(
                convert_archive.s(
                    task_id, file_path, target_format, conversion_params
                )
            )
        else:
            raise Exception(f"Неподдерживаемый формат источника: {source_format}")
        
        # Завершаем задачу успешно
        task.complete()
        
        logger.info(f"Задача {task_id} завершена успешно")
        
        return {
            'success': True,
            'task_id': task_id,
            'result': result
        }
        
    except ConversionTask.DoesNotExist:
        logger.error(f"Задача {task_id} не найдена в базе данных")
        return {'success': False, 'error': 'Задача не найдена'}
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Ошибка при обработке задачи {task_id}: {error_message}")
        
        # Помечаем задачу как неудачную
        if task:
            task.fail(error_message)
        
        return {'success': False, 'error': error_message}
        
    finally:
        # Очищаем временные файлы
        cleanup_files(*temp_files)


@shared_task(bind=True)
def cleanup_old_files(self, max_age_hours=24):
    """
    Периодическая очистка старых временных файлов
    
    Args:
        max_age_hours: Максимальный возраст файлов в часах
    """
    from celery_app import cleanup_temp_files
    
    results = []
    
    # Очистка всех временных директорий
    for temp_type, temp_path in TEMP_DIRS.items():
        full_path = Path(settings.MEDIA_ROOT) / temp_path
        if full_path.exists():
            result = cleanup_temp_files.delay(str(full_path), max_age_hours)
            results.append({
                'directory': temp_type,
                'task_id': result.task_id
            })
    
    # Очистка завершённых задач старше 7 дней
    try:
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=7)
        
        old_tasks = ConversionTask.objects.filter(
            completed_at__lt=cutoff_date,
            status__in=[ConversionTask.STATUS_DONE, ConversionTask.STATUS_FAILED]
        )
        
        deleted_count = old_tasks.count()
        old_tasks.delete()
        
        logger.info(f'Удалено {deleted_count} старых записей задач из базы данных')
        results.append({
            'directory': 'database',
            'deleted_records': deleted_count
        })
        
    except Exception as e:
        logger.error(f'Ошибка при очистке старых задач из БД: {e}')
    
    return {
        'status': 'completed',
        'cleanup_tasks': results,
        'timestamp': timezone.now().isoformat()
    }
