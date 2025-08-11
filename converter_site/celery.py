# -*- coding: utf-8 -*-
"""
Celery конфигурация для Django проекта converter_site
"""

import os
from celery import Celery

# Установка переменной окружения Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')

# Создание экземпляра Celery
app = Celery('converter_site')

# Настройка Celery из Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение задач во всех приложениях Django
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Отладочная задача для тестирования Celery"""
    print(f'Request: {self.request!r}')
