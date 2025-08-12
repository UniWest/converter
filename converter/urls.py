from django.urls import path  
from . import views
from . import api_views_extended

app_name = "converter"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("upload/", views.VideoUploadView.as_view(), name="video_upload"),
    path("convert/", views.convert_video_view, name="convert_video"),
    path("status/", views.converter_status_view, name="converter_status"),
    path("video-info/", views.video_info_view, name="video_info"),  # AJAX endpoint for video info
    path("api/latest-progress/", views.latest_progress, name="latest_progress"),
    path("api/photos-to-gif/", views.api_photos_to_gif_view, name="api_photos_to_gif"),  # API for photos to GIF
    
    # Additional converter views (placeholders for now)
    path("photos-to-gif/", views.photos_to_gif_view, name="photos_to_gif"),
    path("audio-to-text/", views.audio_to_text_view, name="audio_to_text"),
    
    # API endpoint for audio-to-text
    path("api/audio-to-text/", views.api_audio_to_text_view, name="api_audio_to_text"),
    
    # API endpoints for conversion interface
    path("api/conversion/submit/", views.api_conversion_submit, name="api_conversion_submit"),
    path("api/conversion/queue/", views.api_conversion_queue, name="api_conversion_queue"),

    # API endpoints for conversion results management (used by results.html)
    path("api/conversion/results/", api_views_extended.get_conversion_results, name="api_conversion_results"),
    path("api/conversion/download-batch/", api_views_extended.download_batch_results, name="api_conversion_download_batch"),
    path("api/conversion/clear-completed/", api_views_extended.clear_completed_tasks, name="api_conversion_clear_completed"),
    path("api/conversion/results/<int:result_id>/", api_views_extended.delete_conversion_result, name="api_conversion_delete_result"),
    
    path("conversion-interface/", views.conversion_interface_view, name="conversion_interface"),
    path("comprehensive/", views.comprehensive_converter_view, name="comprehensive_converter"),
    
    # API endpoints для универсального конвертера
    path("ajax_convert/", views.ajax_convert_video, name="ajax_convert"),
    path("convert_with_adapters/", views.convert_with_adapters, name="convert_with_adapters"),
    path("engine_status/", views.engine_status, name="engine_status"),
    
    # Новый универсальный API endpoint
    path("api/universal-convert/", views.api_universal_convert, name="api_universal_convert"),
    path("health/", views.health, name="health"),

    # Одноразовая загрузка (скачать и удалить)
    path("download/<str:category>/<str:filename>/", views.download_and_delete, name="download_once"),
    
    # Оптимизированные маршруты скачивания для облачных платформ
    path("download-optimized/<str:category>/<str:filename>/", views.optimized_download, name="optimized_download"),
    path("download-test/", views.download_test, name="download_test"),
]
