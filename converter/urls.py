"""
URL configuration for converter app.
"""

from django.urls import path
from . import views
from . import api_views
from . import views_comprehensive

app_name = 'converter'

urlpatterns = [
    # Главная страница с формой загрузки
    path('', views.home_view, name='home'),
    
    # Обработка конвертации видео
    path('convert/', views.convert_video_view, name='convert_video'),
    
    # Быстрая конвертация с предустановленными настройками
    path('quick-convert/', views.quick_convert_view, name='quick_convert'),
    
    # AJAX конвертация для асинхронной обработки
    path('ajax-convert/', views.ajax_convert_view, name='ajax_convert'),
    
    # Получение информации о видео файле
    path('video-info/', views.video_info_view, name='video_info'),
    
    # Скачивание конвертированного GIF
    path('download/<str:filename>/', views.download_gif_view, name='download_gif'),
    
    # Проверка статуса конвертера
    path('status/', views.converter_status_view, name='converter_status'),
    
    # Тестовый URL для проверки GIF файлов
    path('test-gif/<str:filename>/', views.test_gif_view, name='test_gif'),
    
    # Новые маршруты для интерфейса конвертации
    path('interface/', views.conversion_interface, name='conversion_interface'),
    path('results/', views.conversion_results, name='conversion_results'),
    
    # API маршруты для расширенной функциональности (commented out until api_views_extended is implemented)
    # path('api/submit/', api_views_extended.submit_conversion_task, name='api_submit_task'),
    # path('api/queue/', api_views_extended.get_task_queue, name='api_task_queue'),
    # path('api/results/', api_views_extended.get_conversion_results, name='api_conversion_results'),
    # path('api/task/<int:task_id>/', api_views_extended.get_task_status, name='api_task_status'),
    # path('api/download-batch/', api_views_extended.download_batch_results, name='api_download_batch'),
    # path('api/clear-completed/', api_views_extended.clear_completed_tasks, name='api_clear_completed'),
    # path('api/delete/<int:task_id>/', api_views_extended.delete_conversion_result, name='api_delete_result'),
    # path('api/stats/', api_views_extended.get_conversion_stats, name='api_conversion_stats'),
    
    # Comprehensive converter URLs
    path('comprehensive/', views_comprehensive.comprehensive_converter_view, name='comprehensive_converter'),
    path('convert-universal/', views_comprehensive.universal_convert_view, name='universal_convert'),
    path('engine_status/', views.engine_status, name='engine_status'),
    path('detect-file-type/', views_comprehensive.detect_file_type_view, name='detect_file_type'),
    path('batch-convert/', views_comprehensive.batch_convert_view, name='batch_convert'),
    path('conversion-history/', views_comprehensive.conversion_history_view, name='conversion_history'),
    
    # Дополнительные endpoints: речевое распознавание (Speech-to-Text)
    path('audio-to-text/', views.audio_to_text_page, name='audio_to_text'),
    path('api/audio-to-text/', views.audio_to_text_api, name='api_audio_to_text'),
    
    # Создание GIF из фотографий (Photos-to-GIF)
    path('photos-to-gif/', views.photos_to_gif_page, name='photos_to_gif'),
    path('api/photos-to-gif/', views.photos_to_gif_api, name='api_photos_to_gif'),
    
    # API для работы с задачами (асинхронными)
    path('api/task-status/<str:task_id>/', views.task_status_api, name='api_task_status'),
    path('api/cancel-task/<str:task_id>/', views.cancel_task_api, name='api_cancel_task'),
    
    # Additional adapter-related endpoints
    path('convert_with_adapters/', views_comprehensive.universal_convert_view, name='convert_with_adapters'),
]
