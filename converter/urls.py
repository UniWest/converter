from django.urls import path  
from . import views

app_name = "converter"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("upload/", views.VideoUploadView.as_view(), name="video_upload"),
    path("convert/", views.convert_video_view, name="convert_video"),
    path("status/", views.converter_status_view, name="converter_status"),
]
