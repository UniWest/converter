import os
import uuid
import tempfile
import logging
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from forms import VideoUploadForm
from .models import ConversionTask
from .services import VideoConversionService
from .utils import VideoConverter

logger = logging.getLogger(__name__)

class VideoUploadView(View):
    """
    Dedicated view for handling video uploads and conversion.
    Handles POST requests with VideoUploadForm and saves files to MEDIA_ROOT/tmp.
    """
    
    def get(self, request):
        """Display the upload form."""
        form = VideoUploadForm()
        return render(request, 'converter/home.html', {'form': form})
    
    def post(self, request):
        """Handle video upload and initiate conversion."""
        form = VideoUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Get conversion settings from form
                conversion_settings = form.get_conversion_settings()
                if not conversion_settings:
                    messages.error(request, 'Ошибка валидации настроек конвертации')
                    return render(request, 'converter/home.html', {'form': form})
                
                # Save uploaded file to MEDIA_ROOT/tmp
                uploaded_file = conversion_settings['video_file']
                tmp_dir = Path(settings.MEDIA_ROOT) / 'tmp'
                tmp_dir.mkdir(exist_ok=True)
                
                # Generate unique filename
                file_extension = Path(uploaded_file.name).suffix
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                tmp_file_path = tmp_dir / unique_filename
                
                # Save file
                with open(tmp_file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                logger.info(f"Video uploaded to temporary location: {tmp_file_path}")
                
                # Create conversion task
                task = ConversionTask.objects.create(
                    status=ConversionTask.STATUS_QUEUED
                )
                
                # Set task metadata
                task.set_metadata(
                    original_filename=uploaded_file.name,
                    input_path=str(tmp_file_path),
                    file_size=uploaded_file.size,
                    conversion_params=conversion_settings,
                    file_type='video',
                    input_format=file_extension.lstrip('.').lower()
                )
                task.save()
                
                # Initialize conversion service
                conversion_service = VideoConversionService()
                
                # Perform conversion (synchronous for now)
                try:
                    result = conversion_service.convert_video_to_gif(
                        task_id=task.id,
                        input_path=str(tmp_file_path),
                        **conversion_settings
                    )
                    
                    if result['success']:
                        # Return file download response
                        return self._serve_converted_file(result['output_path'])
                    else:
                        # Handle conversion error
                        error_msg = result.get('error_message', 'Неизвестная ошибка конвертации')
                        messages.error(request, f'Ошибка конвертации: {error_msg}')
                        logger.error(f"Conversion failed for task {task.id}: {error_msg}")
                        
                except Exception as e:
                    error_msg = f'Ошибка при обработке видео: {str(e)}'
                    messages.error(request, error_msg)
                    logger.error(f"Conversion exception for task {task.id}: {e}")
                    
                    # Update task status
                    task.fail(str(e))
                
            except Exception as e:
                error_msg = f'Ошибка при загрузке файла: {str(e)}'
                messages.error(request, error_msg)
                logger.error(f"Upload error: {e}")
        
        else:
            # Form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields[field].label}: {error}')
        
        return render(request, 'converter/home.html', {'form': form})
    
    def _serve_converted_file(self, file_path):
        """Serve the converted GIF file for download."""
        if not os.path.exists(file_path):
            raise Http404("Конвертированный файл не найден")
        
        filename = os.path.basename(file_path)
        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=filename,
            content_type='image/gif'
        )
        
        # Add headers for better download experience
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = os.path.getsize(file_path)
        
        return response

def home_view(request):
    """Redirect to the new upload view."""
    upload_view = VideoUploadView.as_view()
    return upload_view(request)

def convert_video_view(request):
    return render(request, 'converter/index.html', {'form': VideoUploadForm()})

def converter_status_view(request):
    return JsonResponse({'status': 'operational', 'version': '1.0.0'})
