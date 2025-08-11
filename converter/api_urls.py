"""
URL маршруты для API управления задачами конвертации файлов.
"""

from django.urls import path
from . import api_views

urlpatterns = [
    # Создание новой задачи конвертации
    # POST /api/tasks/create/ - multipart form или JSON с URL
    path('create/', api_views.create_task_view, name='api_task_create'),
    
    # Получение статуса задачи
    # GET /api/tasks/<task_id>/status/
    path('<int:task_id>/status/', api_views.task_status_view, name='api_task_status'),
    
    # Получение результата задачи
    # GET /api/tasks/<task_id>/result/
    path('<int:task_id>/result/', api_views.task_result_view, name='api_task_result'),
    
    # Скачивание результата задачи
    # GET /api/tasks/<task_id>/download/
    path('<int:task_id>/download/', api_views.task_download_view, name='api_task_download'),
    
    # Список всех задач с пагинацией и фильтрацией
    # GET /api/tasks/
    path('', api_views.tasks_list_view, name='api_tasks_list'),
    
    # Пакетное скачивание нескольких задач в ZIP
    # GET /api/tasks/batch-download/?task_ids=1,2,3,4
    # POST /api/tasks/batch-download/ {"task_ids": [1,2,3,4]}
    path('batch-download/', api_views.batch_download_view, name='api_batch_download'),
]
