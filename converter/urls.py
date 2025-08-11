from django.urls import path  
from . import views

app_name = "converter"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("upload/", views.VideoUploadView.as_view(), name="video_upload"),
    path("convert/", views.convert_video_view, name="convert_video"),
    path("status/", views.converter_status_view, name="converter_status"),
    
    # Additional converter views (placeholders for now)
    path("photos-to-gif/", views.photos_to_gif_view, name="photos_to_gif"),
    path("audio-to-text/", views.audio_to_text_view, name="audio_to_text"),
    path("conversion-interface/", views.conversion_interface_view, name="conversion_interface"),
    path("comprehensive/", views.comprehensive_converter_view, name="comprehensive_converter"),
]
