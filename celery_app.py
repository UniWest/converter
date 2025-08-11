# -*- coding: utf-8 -*-
"""
Конфигурация Celery для обработки файлов в фоновом режиме
Аналогично системе очередей в Convertio
"""

import os
import logging
from celery import Celery
from celery.signals import worker_ready, task_prerun, task_postrun, task_failure
from converter_settings import REDIS_URL

# Установка переменной окружения Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')

# Создание экземпляра Celery
app = Celery('file_converter')

# Конфигурация Celery
app.conf.update(
    # Брокер сообщений (Redis)
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    
    # Настройки задач
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Настройки воркеров
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Маршрутизация задач
    task_routes={
        'converter.tasks.convert_video': {'queue': 'video'},
        'converter.tasks.convert_audio': {'queue': 'audio'},
        'converter.tasks.convert_image': {'queue': 'image'},
        'converter.tasks.convert_document': {'queue': 'document'},
        'converter.tasks.convert_archive': {'queue': 'archive'},
    },
    
    # Настройки результатов
    result_expires=3600,  # Результаты хранятся 1 час
    
    # Настройки мониторинга
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Автоматическое обнаружение задач
app.autodiscover_tasks(['converter'])

# Настройка логирования
logger = logging.getLogger(__name__)

@worker_ready.connect
def worker_ready_handler(**kwargs):
    """Обработчик готовности воркера"""
    logger.info('Воркер Celery готов к работе')

@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Обработчик перед выполнением задачи"""
    logger.info(f'Начинаем выполнение задачи: {task.name} [{task_id}]')
    
    # Обновляем статус задачи в базе данных
    from converter.models import ConversionTask
    try:
        task_obj = ConversionTask.objects.get(id=task_id)
        task_obj.start()
        logger.info(f'Статус задачи {task_id} обновлён на "running"')
    except ConversionTask.DoesNotExist:
        logger.warning(f'Задача {task_id} не найдена в базе данных')
    except Exception as e:
        logger.error(f'Ошибка обновления статуса задачи {task_id}: {e}')

@task_postrun.connect
def task_postrun_handler(task_id, task, retval, state, *args, **kwargs):
    """Обработчик после выполнения задачи"""
    from converter.models import ConversionTask
    
    logger.info(f'Задача {task.name} [{task_id}] завершена со статусом: {state}')
    
    # Обновляем статус задачи в базе данных
    try:
        task_obj = ConversionTask.objects.get(id=task_id)
        if state == 'SUCCESS':
            task_obj.complete()
            logger.info(f'Задача {task_id} успешно завершена')
        elif state == 'FAILURE':
            error_msg = str(retval) if retval else 'Неизвестная ошибка'
            task_obj.fail(error_msg)
            logger.error(f'Задача {task_id} завершена с ошибкой: {error_msg}')
    except ConversionTask.DoesNotExist:
        logger.warning(f'Задача {task_id} не найдена в базе данных')
    except Exception as e:
        logger.error(f'Ошибка обновления статуса задачи {task_id}: {e}')

@task_failure.connect
def task_failure_handler(task_id, exception, einfo, *args, **kwargs):
    """Обработчик ошибок задач"""
    from converter.models import ConversionTask
    
    logger.error(f'Ошибка в задаче {task_id}: {exception}')
    logger.error(f'Трассировка: {einfo}')
    
    # Обновляем статус задачи в базе данных
    try:
        task_obj = ConversionTask.objects.get(id=task_id)
        task_obj.fail(str(exception))
        logger.info(f'Статус задачи {task_id} обновлён на "failed"')
    except ConversionTask.DoesNotExist:
        logger.warning(f'Задача {task_id} не найдена в базе данных')
    except Exception as e:
        logger.error(f'Ошибка обновления статуса задачи {task_id}: {e}')

@app.task(bind=True)
def debug_task(self):
    """Отладочная задача"""
    logger.info(f'Debug task request: {self.request!r}')
    return f'Debug task completed successfully'

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def cleanup_temp_files(self, directory_path, max_age_hours=24):
    """
    Очистка временных файлов
    
    Args:
        directory_path (str): Путь к директории с временными файлами
        max_age_hours (int): Максимальный возраст файлов в часах
    """
    import time
    import shutil
    from pathlib import Path
    
    try:
        cleanup_path = Path(directory_path)
        if not cleanup_path.exists():
            logger.info(f'Директория {directory_path} не существует, пропускаем')
            return {'status': 'skipped', 'reason': 'директория не существует'}
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        deleted_files = 0
        deleted_dirs = 0
        total_size = 0
        
        # Очистка файлов
        for item in cleanup_path.rglob('*'):
            try:
                item_age = current_time - item.stat().st_mtime
                if item_age > max_age_seconds:
                    if item.is_file():
                        file_size = item.stat().st_size
                        item.unlink()
                        deleted_files += 1
                        total_size += file_size
                        logger.debug(f'Удалён файл: {item}')
                    elif item.is_dir() and not any(item.iterdir()):
                        item.rmdir()
                        deleted_dirs += 1
                        logger.debug(f'Удалёна пустая директория: {item}')
            except (OSError, IOError) as e:
                logger.warning(f'Ошибка при удалении {item}: {e}')
                continue
        
        result = {
            'status': 'success',
            'deleted_files': deleted_files,
            'deleted_dirs': deleted_dirs,
            'freed_space_mb': round(total_size / (1024 * 1024), 2),
            'directory': str(directory_path)
        }
        
        logger.info(f'Очистка завершена: {result}')
        return result
        
    except Exception as exc:
        logger.error(f'Ошибка при очистке {directory_path}: {exc}')
        
        # Повторная попытка через минуту
        if self.request.retries < self.max_retries:
            logger.info(f'Повторная попытка очистки {directory_path} через {self.default_retry_delay} секунд')
            raise self.retry(exc=exc)
        else:
            logger.error(f'Превышено максимальное количество попыток очистки {directory_path}')
            return {'status': 'failed', 'error': str(exc)}

if __name__ == '__main__':
    app.start()
