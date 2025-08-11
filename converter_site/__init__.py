# -*- coding: utf-8 -*-
"""
Инициализация Celery для Django проекта
Обеспечивает автоматическую загрузку Celery при старте Django
"""

# Импортируем Celery приложение для автоматической загрузки
# Делаем импорт опциональным для возможности запуска без Redis
try:
    from .celery_app import app as celery_app
    __all__ = ('celery_app',)
except ImportError as e:
    print(f"Предупреждение: Celery недоступен - {e}")
    print("Django будет работать без фоновых задач")
    celery_app = None
    __all__ = ()
