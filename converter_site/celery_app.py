import os
import logging

try:
    from celery import Celery
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    print("Предупреждение: Celery не установлен. Фоновые задачи недоступны.")
    CELERY_AVAILABLE = False
    Celery = None
    crontab = None

from django.conf import settings

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Устанавливаем переменную окружения Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')

# Создаем экземпляр Celery только если Celery доступен
if CELERY_AVAILABLE:
    app = Celery('converter_site')
    
    # Основные настройки Celery
    app.conf.update(
        # Брокер сообщений (Redis)
        broker_url=getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        
        # Backend для результатов (Redis)
        result_backend=getattr(settings, 'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        
        # Таймауты
        task_time_limit=7200,          # 2 часа максимум на задачу
        task_soft_time_limit=6600,     # 1 час 50 минут мягкий лимит
        worker_prefetch_multiplier=1,   # Один таск на воркер
        
        # Сериализация
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        
        # Часовой пояс
        timezone='Europe/Moscow',
        enable_utc=True,
        
        # Результаты
        result_expires=3600,            # Результаты хранятся 1 час
        task_track_started=True,        # Отслеживание запуска задач
        task_ignore_result=False,       # Сохраняем результаты
        
        # Маршрутизация задач
        task_routes={
            'converter_site.tasks.convert_audio_to_text': {'queue': 'audio_processing'},
            'converter_site.tasks.create_gif_from_images': {'queue': 'image_processing'},
            'converter_site.tasks.cleanup_old_files': {'queue': 'maintenance'},
        },
        
        # Конфигурация воркеров
        worker_max_tasks_per_child=50,     # Максимум задач на процесс
        worker_disable_rate_limits=True,   # Отключаем ограничения скорости
        worker_concurrency=2,              # Количество процессов
        
        # Мониторинг и логирование
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Настройки повторных попыток
        task_default_retry_delay=60,       # 1 минута между повторами
        task_max_retries=3,                # Максимум 3 повтора
        
        # Расписание для периодических задач
        beat_schedule={
            # Очистка старых временных файлов каждый день в 3:00
            'cleanup-temp-files': {
                'task': 'converter_site.tasks.cleanup_old_files',
                'schedule': crontab(hour=3, minute=0),
                'args': (1,)  # удалять файлы старше 1 дня
            },
        },
    )

    # Автопоиск задач в Django приложениях
    app.autodiscover_tasks()

    # Специальные настройки для разных типов задач
    app.conf.task_annotations = {
        # Задачи обработки аудио
        'converter_site.tasks.convert_audio_to_text': {
            'time_limit': 3600,         # 1 час
            'soft_time_limit': 3300,    # 55 минут
            'max_retries': 2,
            'default_retry_delay': 120,
        },
        
        # Задачи создания GIF
        'converter_site.tasks.create_gif_from_images': {
            'time_limit': 1800,         # 30 минут
            'soft_time_limit': 1500,    # 25 минут
            'max_retries': 2,
            'default_retry_delay': 60,
        },
        
        # Задачи очистки
        'converter_site.tasks.cleanup_old_files': {
            'time_limit': 300,          # 5 минут
            'soft_time_limit': 240,     # 4 минуты
            'max_retries': 1,
        }
    }

    # Конфигурация очередей
    app.conf.task_default_queue = 'default'
    app.conf.task_queues = {
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'audio_processing': {
            'exchange': 'audio_processing',
            'routing_key': 'audio_processing',
        },
        'image_processing': {
            'exchange': 'image_processing',
            'routing_key': 'image_processing',
        },
        'maintenance': {
            'exchange': 'maintenance',
            'routing_key': 'maintenance',
        }
    }

    # Настройки безопасности
    app.conf.worker_hijack_root_logger = False
    app.conf.worker_log_color = False

    # Обработчики событий
    @app.task(bind=True)
    def debug_task(self):
        """Отладочная задача для проверки работы Celery."""
        logger.info(f'Request: {self.request!r}')
        return 'Debug task completed successfully'


    # Хуки для обработки событий задач
    @app.task(bind=True, base=app.Task)
    def task_failure_handler(self, task_id, error, traceback):
        """Обработчик ошибок задач."""
        logger.error(f'Task {task_id} failed: {error}')
        # Здесь можно добавить отправку уведомлений или логирование в БД


    @app.task(bind=True)
    def task_success_handler(self, task_id, result):
        """Обработчик успешного завершения задач."""
        logger.info(f'Task {task_id} completed successfully')
        # Здесь можно добавить дополнительную обработку результатов


    # Настройки для разработки и продакшена
    if settings.DEBUG:
        # В режиме разработки
        app.conf.update(
            task_always_eager=False,    # Выполнять задачи асинхронно
            task_eager_propagates=True, # Распространять исключения в eager режиме
            worker_pool='solo',         # Один процесс для разработки
        )
    else:
        # В продакшене
        app.conf.update(
            worker_pool='prefork',      # Многопроцессорный пул
            worker_concurrency=4,       # Больше процессов в продакшене
            task_compression='gzip',    # Сжатие задач
            result_compression='gzip',  # Сжатие результатов
        )

    logger.info("Celery application configured successfully")

else:
    # Celery недоступен - создаем заглушку
    app = None
    debug_task = None
    task_failure_handler = None 
    task_success_handler = None
    logger.info("Django running without Celery (task queue unavailable)")
