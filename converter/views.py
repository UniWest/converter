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
                
                # Extract uploaded file separately (can't be JSON serialized)
                uploaded_file = conversion_settings.pop('video_file')
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

# Additional placeholder views for navigation links
def photos_to_gif_view(request):
    """View for photos to GIF conversion."""
    return render(request, 'converter/photos_to_gif.html')

def audio_to_text_view(request):
    """View for audio to text conversion."""
    return render(request, 'converter/audio_to_text.html')

def conversion_interface_view(request):
    """View for conversion interface."""
    return render(request, 'converter/conversion_interface.html')

def comprehensive_converter_view(request):
    """View for comprehensive converter."""
    return render(request, 'converter/comprehensive_converter.html')

@require_http_methods(["POST"])
@csrf_exempt
def video_info_view(request):
    """Get video information via AJAX."""
    if not request.FILES.get('video'):
        return JsonResponse({'success': False, 'error': 'No video file provided'})
    
    try:
        video_file = request.FILES['video']
        converter = VideoConverter()
        info = converter.get_video_info(video_file)
        
        if info:
            return JsonResponse({
                'success': True,
                'info': info
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Could not extract video information'
            })
            
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Server error while processing video'
        })

@require_http_methods(["POST"])
@csrf_exempt
def api_photos_to_gif_view(request):
    """API endpoint for converting photos to GIF."""
    try:
        from .utils import PhotoToGifConverter
        import tempfile
        import uuid
        
        # Check if images are provided
        images = request.FILES.getlist('images')
        if not images:
            return JsonResponse({
                'success': False,
                'error': 'No images provided'
            })
        
        # Get parameters from request
        frame_duration = float(request.POST.get('frame_duration', 0.5)) * 1000  # Convert to milliseconds
        output_size = request.POST.get('output_size', '480')
        colors = int(request.POST.get('colors', 128))
        loop = request.POST.get('loop', 'true').lower() == 'true'
        sort_order = request.POST.get('sort_order', 'filename')
        pingpong = request.POST.get('pingpong', 'false').lower() == 'true'
        optimize = request.POST.get('optimize', 'true').lower() == 'true'
        
        # Sort images if needed
        if sort_order == 'filename':
            images = sorted(images, key=lambda x: x.name)
        # Add more sorting options if needed
        
        # Determine output size
        resize = None
        if output_size != 'original' and output_size.isdigit():
            size = int(output_size)
            resize = (size, size)
        
        # Create temporary output file
        temp_dir = Path(settings.MEDIA_ROOT) / 'temp'
        temp_dir.mkdir(exist_ok=True)
        
        output_filename = f"photos_to_gif_{uuid.uuid4().hex[:8]}.gif"
        output_path = temp_dir / output_filename
        
        # Initialize converter
        converter = PhotoToGifConverter()
        
        # Convert photos to GIF
        success = converter.create_gif_from_photos(
            photo_files=images,
            output_path=str(output_path),
            duration=int(frame_duration),
            loop=0 if loop else 1,
            quality=85,
            resize=resize,
            reverse=pingpong,
            optimize=optimize
        )
        
        if success and output_path.exists():
            # Move to final location
            final_dir = Path(settings.MEDIA_ROOT) / 'gifs'
            final_dir.mkdir(exist_ok=True)
            
            final_filename = f"photos_{uuid.uuid4().hex[:8]}.gif"
            final_path = final_dir / final_filename
            
            import shutil
            shutil.move(str(output_path), str(final_path))
            
            # Generate URL
            gif_url = f"{settings.MEDIA_URL}gifs/{final_filename}"
            
            # Get file info
            file_size = final_path.stat().st_size
            total_duration = len(images) * (frame_duration / 1000)
            
            return JsonResponse({
                'success': True,
                'gif_url': gif_url,
                'file_info': {
                    'frames': len(images),
                    'duration_per_frame': frame_duration / 1000,
                    'total_duration': total_duration,
                    'file_size': file_size,
                    'dimensions': f"{resize[0]}x{resize[1]}" if resize else 'Original'
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create GIF from photos'
            })
            
    except Exception as e:
        logger.error(f"Error creating GIF from photos: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })
