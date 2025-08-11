from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from converter.healthcheck import health_check

urlpatterns = [
    # Healthcheck for Railway/Render
    path('health/', health_check, name='health_check'),
    path('', health_check, name='root_health_check'),  # For root path
    
    # Favicon
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),
    
    path('admin/', admin.site.urls),
    # Web interface for converter
    path('app/', include(('converter.urls', 'converter'), namespace='converter')),
]

# Serve media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
