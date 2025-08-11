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
]
