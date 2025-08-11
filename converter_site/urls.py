from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from converter.healthcheck import health_check
from converter.views import home_view

urlpatterns = [
    # Home page - proper web interface
    path('', home_view, name='home'),
    
    # Healthcheck for Railway/Render (separate endpoint)
    path('health/', health_check, name='health_check'),
    path('status/', health_check, name='status_check'),  # Alternative health endpoint
    
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
