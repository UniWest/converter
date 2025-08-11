"""
Comprehensive file converter views that integrate existing video conversion 
with the new adapter system for images, audio, documents, and archives.
"""

import os
import tempfile
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.conf import settings

# Import existing utilities
from .utils import save_converted_gif, cleanup_temp_files

# Import adapter system
try:
    from .adapters import engine_manager, VideoEngine, ImageEngine, AudioEngine, DocumentEngine, ArchiveEngine
    from .adapters.base import ConversionResult
    ADAPTERS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Adapters not available: {e}")
    ADAPTERS_AVAILABLE = False
    # Create dummy objects to prevent further errors
    engine_manager = None

# Import existing forms for backward compatibility
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from forms import VideoUploadForm
except ImportError:
    VideoUploadForm = None

logger = logging.getLogger(__name__)


def comprehensive_converter_view(request):
    """
    Main comprehensive converter interface that supports all file types.
    """
    context = {
        'adapters_available': ADAPTERS_AVAILABLE,
        'engine_status': {},
        'supported_formats': {}
    }
    
    # Load engine status if adapters are available
    if ADAPTERS_AVAILABLE and engine_manager:
        try:
            context['engine_status'] = engine_manager.get_engine_status()
            context['supported_formats'] = engine_manager.get_supported_formats()
        except Exception as e:
            logger.error(f"Error loading engine status: {e}")
            context['adapters_available'] = False
    
    return render(request, 'converter/comprehensive_converter.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def universal_convert_view(request):
    """
    Universal conversion endpoint that handles all file types through the adapter system.
    Falls back to existing video conversion for backward compatibility.
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'Файл не найден'
            })

        input_file = request.FILES['file']
        
        # Get conversion parameters
        output_format = request.POST.get('output_format', 'auto')
        engine_type = request.POST.get('engine_type')  # Optional specific engine
        
        # Detect file type if not specified
        if not engine_type:
            file_extension = input_file.name.lower().split('.')[-1]
            engine_type = detect_file_type_by_extension(file_extension)
        
        # Route to appropriate conversion method
        if engine_type == 'video':
            return handle_video_conversion(request, input_file)
        elif engine_type == 'image' and ADAPTERS_AVAILABLE:
            return handle_image_conversion(request, input_file)
        elif engine_type in ['audio', 'document', 'archive'] and ADAPTERS_AVAILABLE:
            return handle_adapter_conversion(request, input_file, engine_type)
        else:
            return JsonResponse({
                'success': False,
                'error': f'Тип файла "{engine_type}" пока не поддерживается'
            })
            
    except Exception as e:
        logger.error(f"Universal conversion error: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка: {str(e)}'
        })


def handle_video_conversion(request, video_file):
    """
    Handle video conversion using the existing video converter.
    """
    try:
        # Import existing video converter
        from .utils import VideoConverter
        
        # Get video-specific parameters
        params = {
            'width': request.POST.get('width'),
            'fps': int(request.POST.get('fps', 15)),
            'start_time': int(request.POST.get('start_time', 0)),
            'end_time': request.POST.get('end_time'),
            'keep_original_size': request.POST.get('keep_original_size') in ['true', 'on', '1'],
            'speed': float(request.POST.get('speed', '1.0') or 1.0),
            'grayscale': request.POST.get('grayscale') in ['true', 'on', '1'],
            'reverse': request.POST.get('reverse') in ['true', 'on', '1'],
            'boomerang': request.POST.get('boomerang') in ['true', 'on', '1'],
            'high_quality': request.POST.get('high_quality') in ['true', 'on', '1'],
            'dither': request.POST.get('dither', 'bayer'),
        }
        
        # Clean None values
        params = {k: v for k, v in params.items() 
                 if v is not None and v != '' and v != 'None'}
        
        # Convert width to int if present
        if 'width' in params and params['width']:
            params['width'] = int(params['width'])
        if 'end_time' in params and params['end_time']:
            params['end_time'] = int(params['end_time'])
        
        # Create converter
        converter = VideoConverter(use_moviepy=True)
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_gif:
            temp_gif_path = temp_gif.name
        
        try:
            # Perform conversion
            success = converter.convert_video_to_gif(
                video_file,
                temp_gif_path,
                **params
            )
            
            if success and os.path.exists(temp_gif_path):
                # Save GIF using existing utility
                gif_url = save_converted_gif(temp_gif_path, video_file.name)
                
                if gif_url:
                    # Get video info
                    try:
                        video_info = converter.get_video_info(video_file)
                    except:
                        video_info = {}
                    
                    return JsonResponse({
                        'success': True,
                        'gif_url': gif_url,
                        'output_url': gif_url,  # For compatibility
                        'video_info': video_info,
                        'metadata': {
                            'original_filename': video_file.name,
                            'output_format': 'gif',
                            'conversion_params': params
                        },
                        'message': 'Видео успешно конвертировано в GIF!'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Ошибка при сохранении GIF файла'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Ошибка при конвертации видео'
                })
        finally:
            cleanup_temp_files([temp_gif_path])
            
    except Exception as e:
        logger.error(f"Video conversion error: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при конвертации видео: {str(e)}'
        })


def handle_image_conversion(request, image_file):
    """
    Handle image conversion using the ImageEngine adapter.
    Also supports creating GIF (including simple animated GIF) from an image.
    """
    try:
        # Get image-specific parameters
        width = request.POST.get('width')
        height = request.POST.get('height')
        output_format = (request.POST.get('output_format') or 'jpg').lower()
        quality = int(request.POST.get('quality', 90))

        # If target is GIF, optionally create animated GIF using UI parameters
        if output_format == 'gif':
            # Read GIF-related params
            create_anim = request.POST.get('create_animated_gif') in ['1', 'true', 'on']
            gif_effect = request.POST.get('gif_effect', 'none')
            try:
                gif_duration = int(request.POST.get('gif_duration', 200))  # ms per frame
            except (TypeError, ValueError):
                gif_duration = 200
            try:
                gif_frames = int(request.POST.get('gif_frames', 10))
            except (TypeError, ValueError):
                gif_frames = 10
            gif_loop = 0 if request.POST.get('gif_loop') in ['0', 'false', 'off'] else 0  # 0 = infinite

            # Create temp gif path
            with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as tmp:
                temp_gif_path = tmp.name

            try:
                created = create_animated_gif_from_image(
                    image_file=image_file,
                    output_path=temp_gif_path,
                    frames=gif_frames if create_anim else 1,
                    duration=gif_duration,
                    effect=gif_effect if create_anim else 'none',
                    width=int(width) if width else None,
                    height=int(height) if height else None,
                    loop=gif_loop
                )
                if not created:
                    return JsonResponse({'success': False, 'error': 'Не удалось создать GIF из изображения'})

                # Save to media using existing GIF saver
                gif_url = save_converted_gif(temp_gif_path, image_file.name)
                if gif_url:
                    return JsonResponse({
                        'success': True,
                        'gif_url': gif_url,
                        'output_url': gif_url,
                        'message': 'GIF успешно создан из изображения'
                    })
                else:
                    return JsonResponse({'success': False, 'error': 'Ошибка при сохранении GIF результата'})
            finally:
                cleanup_temp_files([temp_gif_path])

        # Otherwise, for non-GIF formats, check if ImageEngine is available
        if not ADAPTERS_AVAILABLE:
            return JsonResponse({
                'success': False,
                'error': 'Image conversion не поддерживается - адаптеры недоступны'
            })
            
        image_engine = ImageEngine()

        # Check availability
        if not image_engine.is_available():
            deps = image_engine.check_dependencies()
            return JsonResponse({
                'success': False,
                'error': f'Image engine недоступен. Статус зависимостей: {deps}'
            })

        # Create temporary output file
        temp_output_path = tempfile.mktemp(suffix=f'.{output_format}')

        try:
            # Prepare conversion parameters
            conversion_params = {}
            if width:
                conversion_params['width'] = int(width)
            if height:
                conversion_params['height'] = int(height)
            conversion_params['quality'] = quality
            conversion_params['format'] = output_format

            # Perform conversion
            result = image_engine.convert(
                input_file=image_file,
                output_path=temp_output_path,
                **conversion_params
            )

            if result.success:
                output_url = save_converted_image(temp_output_path, image_file.name, output_format)
                if output_url:
                    return JsonResponse({
                        'success': True,
                        'output_url': output_url,
                        'metadata': result.metadata,
                        'message': f'Изображение успешно конвертировано в {output_format.upper()}!'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Ошибка при сохранении результата'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.error_message
                })
        finally:
            cleanup_temp_files([temp_output_path])

    except Exception as e:
        logger.error(f"Image conversion error: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при конвертации изображения: {str(e)}'
        })


def create_animated_gif_from_image(image_file, output_path, frames=10, duration=200, effect='fade', width=None, height=None, loop=0):
    """
    Create a GIF (optionally animated) from a single image using Pillow.
    - frames: number of frames (1 for static)
    - duration: milliseconds per frame
    - effect: 'none' | 'fade' | 'zoom' | 'rotate' | 'bounce' | 'pan_left' | 'pan_right' | 'pan_up' | 'pan_down' | 'shake' | 'blur'
    - width/height: optional resize
    - loop: 0 for infinite
    Returns True if created successfully.
    """
    try:
        from PIL import Image, ImageFilter
        import io

        # Normalize effect key
        effect = (effect or 'none').replace('-', '_').lower()

        # Read uploaded image into PIL
        if hasattr(image_file, 'read'):
            data = image_file.read()
            img = Image.open(io.BytesIO(data)).convert('RGBA')
        else:
            img = Image.open(image_file).convert('RGBA')

        # Resize if requested
        if width or height:
            target_w = int(width) if width else None
            target_h = int(height) if height else None
            if target_w and not target_h:
                ratio = target_w / img.width
                target_h = max(1, int(img.height * ratio))
            elif target_h and not target_w:
                ratio = target_h / img.height
                target_w = max(1, int(img.width * ratio))
            img = img.resize((target_w or img.width, target_h or img.height), Image.LANCZOS)

        # If only one frame requested or no effect -> save static GIF
        frames_count = max(1, int(frames or 1))
        if frames_count == 1 or effect == 'none':
            img.convert('P', palette=Image.ADAPTIVE).save(
                output_path,
                format='GIF',
                save_all=False,
                optimize=True,
                loop=loop,
            )
            return True

        # Generate frames for simple effects
        frames_list = []
        base = img
        for i in range(frames_count):
            t = i / max(1, frames_count - 1)
            frame = base
            if effect == 'fade':
                # Fade in from 50% to 100%
                alpha = int(128 + t * 127)
                frame = base.copy()
                frame.putalpha(alpha)
            elif effect == 'zoom':
                # Zoom from 95% to 105%
                scale = 0.95 + 0.10 * t
                nw = max(1, int(base.width * scale))
                nh = max(1, int(base.height * scale))
                resized = base.resize((nw, nh), Image.LANCZOS)
                canvas = Image.new('RGBA', base.size, (255, 255, 255, 0))
                x = (base.width - nw) // 2
                y = (base.height - nh) // 2
                canvas.paste(resized, (x, y), resized)
                frame = canvas
            elif effect == 'rotate':
                angle = int(-10 + 20 * t) * 9  # ~ -90..+90 degrees
                frame = base.rotate(angle, resample=Image.BICUBIC, expand=False)
            elif effect == 'bounce':
                # Vertical bounce by 10% height
                offset = int((0.1 * base.height) * (1 - abs(2 * t - 1)))
                canvas = Image.new('RGBA', base.size, (255, 255, 255, 0))
                canvas.paste(base, (0, -offset), base)
                frame = canvas
            elif effect in ('pan_left', 'pan_right', 'pan_up', 'pan_down'):
                # Pan by up to 10% of size
                max_dx = int(0.1 * base.width)
                max_dy = int(0.1 * base.height)
                dx = int(max_dx * t)
                dy = int(max_dy * t)
                ox = -dx if effect == 'pan_left' else (dx if effect == 'pan_right' else 0)
                oy = -dy if effect == 'pan_up' else (dy if effect == 'pan_down' else 0)
                canvas = Image.new('RGBA', base.size, (255, 255, 255, 0))
                canvas.paste(base, (ox, oy), base)
                frame = canvas
            elif effect == 'shake':
                # Small random jitter
                import math
                import random
                jitter = int(2 + 3 * math.sin(i))
                ox = random.choice([-jitter, 0, jitter])
                oy = random.choice([-jitter, 0, jitter])
                canvas = Image.new('RGBA', base.size, (255, 255, 255, 0))
                canvas.paste(base, (ox, oy), base)
                frame = canvas
            elif effect == 'blur':
                radius = 0.1 + 2.9 * t
                frame = base.filter(ImageFilter.GaussianBlur(radius))
            else:
                frame = base

            frames_list.append(frame.convert('P', palette=Image.ADAPTIVE))

        frames_list[0].save(
            output_path,
            format='GIF',
            save_all=True,
            append_images=frames_list[1:],
            duration=max(10, int(duration)),
            loop=loop,
            disposal=2,
            optimize=True,
        )
        return True

    except Exception as e:
        logger.error(f"Error creating animated GIF: {e}")
        return False


def handle_adapter_conversion(request, input_file, engine_type):
    """
    Handle conversion using the specified adapter engine.
    This is a placeholder for future implementations of audio, document, and archive engines.
    """
    try:
        # Check if engine_manager is available
        if not engine_manager:
            return JsonResponse({
                'success': False,
                'error': f'Engine manager недоступен для типа {engine_type}'
            })
            
        # Get the appropriate engine
        engine = engine_manager.get_engine(engine_type)
        
        if not engine:
            return JsonResponse({
                'success': False,
                'error': f'Engine для типа {engine_type} не найден'
            })
        
        if not engine.is_available():
            deps = engine.check_dependencies()
            return JsonResponse({
                'success': False,
                'error': f'{engine_type.capitalize()} engine недоступен. Статус зависимостей: {deps}'
            })
        
        # This is a placeholder - actual implementation depends on the specific engine
        return JsonResponse({
            'success': False,
            'error': f'Конвертация {engine_type} файлов находится в разработке'
        })
        
    except Exception as e:
        logger.error(f"{engine_type} conversion error: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при конвертации {engine_type}: {str(e)}'
        })


def save_converted_image(temp_path, original_filename, output_format):
    """
    Save converted image to media directory (similar to save_converted_gif).
    """
    try:
        import shutil
        from django.core.files.storage import default_storage
        from django.utils.crypto import get_random_string
        
        # Create images directory if it doesn't exist
        images_dir = os.path.join(settings.MEDIA_ROOT, 'images')
        os.makedirs(images_dir, exist_ok=True)
        
        # Generate unique filename
        base_name = os.path.splitext(original_filename)[0]
        random_suffix = get_random_string(8)
        filename = f"{base_name}_{random_suffix}.{output_format}"
        
        # Copy file to media directory
        destination_path = os.path.join(images_dir, filename)
        shutil.copy2(temp_path, destination_path)
        
        # Return URL
        return f"{settings.MEDIA_URL}images/{filename}"
        
    except Exception as e:
        logger.error(f"Error saving converted image: {e}")
        return None


def detect_file_type_by_extension(extension):
    """
    Detect file type based on file extension.
    """
    extension = extension.lower()
    
    type_mapping = {
        # Video
        'mp4': 'video', 'avi': 'video', 'mov': 'video', 'mkv': 'video', 
        'webm': 'video', 'flv': 'video', 'm4v': 'video', 'wmv': 'video',
        'mpg': 'video', 'mpeg': 'video', '3gp': 'video', 'ogg': 'video', 'ogv': 'video',
        
        # Images
        'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image', 
        'bmp': 'image', 'webp': 'image', 'tiff': 'image', 'tif': 'image',
        'svg': 'image', 'ico': 'image', 'heic': 'image', 'heif': 'image',
        
        # Audio
        'mp3': 'audio', 'wav': 'audio', 'flac': 'audio', 'ogg': 'audio',
        'aac': 'audio', 'm4a': 'audio', 'wma': 'audio', 'opus': 'audio',
        
        # Documents
        'pdf': 'document', 'doc': 'document', 'docx': 'document', 
        'rtf': 'document', 'odt': 'document', 'txt': 'document', 
        'md': 'document', 'html': 'document', 'htm': 'document',
        
        # Archives
        'zip': 'archive', 'rar': 'archive', '7z': 'archive', 'tar': 'archive',
        'gz': 'archive', 'bz2': 'archive', 'xz': 'archive'
    }
    
    return type_mapping.get(extension, 'unknown')


@require_http_methods(["GET"])
def engine_status_view(request):
    """
    Return the status of all conversion engines.
    """
    try:
        if not ADAPTERS_AVAILABLE or not engine_manager:
            return JsonResponse({
                'adapters_available': False,
                'error': 'Adapter system not available'
            })
        
        status = engine_manager.get_engine_status()
        
        # Add additional system information
        import platform
        import psutil
        from datetime import datetime
        
        system_info = {
            'timestamp': datetime.now().isoformat(),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
        }
        
        return JsonResponse({
            'adapters_available': True,
            'engines': status,
            'system_info': system_info
        })
        
    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        return JsonResponse({
            'adapters_available': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
def detect_file_type_view(request):
    """
    Detect file type from uploaded file.
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'Файл не найден'
            })
        
        file = request.FILES['file']
        extension = file.name.lower().split('.')[-1]
        detected_type = detect_file_type_by_extension(extension)
        
        # Get additional file info
        file_info = {
            'name': file.name,
            'size': file.size,
            'content_type': file.content_type,
            'detected_type': detected_type,
            'extension': extension
        }
        
        # Check if type is supported
        supported = detected_type in ['video', 'image']  # Currently only these are fully implemented
        
        return JsonResponse({
            'success': True,
            'file_info': file_info,
            'supported': supported,
            'message': f'Файл определен как {detected_type}'
        })
        
    except Exception as e:
        logger.error(f"Error detecting file type: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при определении типа файла: {str(e)}'
        })


def batch_convert_view(request):
    """
    Handle batch conversion of multiple files.
    This is a placeholder for future batch processing functionality.
    """
    if request.method == 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Пакетная конвертация находится в разработке'
        })
    
    return render(request, 'converter/batch_converter.html')


def conversion_history_view(request):
    """
    Show conversion history and statistics.
    """
    from .models import ConversionHistory
    from django.db.models import Count, Avg, Q
    from django.utils import timezone
    from datetime import timedelta
    
    # Получаем параметры фильтрации
    file_type_filter = request.GET.get('file_type', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    period_filter = request.GET.get('period', 'all')
    
    # Базовый запрос
    queryset = ConversionHistory.objects.all()
    
    # Применяем фильтры
    if file_type_filter:
        queryset = queryset.filter(file_type=file_type_filter)
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if search_query:
        queryset = queryset.filter(
            Q(original_filename__icontains=search_query) |
            Q(output_filename__icontains=search_query)
        )
    
    # Фильтр по времени
    now = timezone.now()
    if period_filter == 'today':
        queryset = queryset.filter(created_at__date=now.date())
    elif period_filter == 'week':
        week_ago = now - timedelta(days=7)
        queryset = queryset.filter(created_at__gte=week_ago)
    elif period_filter == 'month':
        month_ago = now - timedelta(days=30)
        queryset = queryset.filter(created_at__gte=month_ago)
    
    # Статистика
    total_conversions = ConversionHistory.objects.count()
    successful_conversions = ConversionHistory.objects.filter(
        status=ConversionHistory.STATUS_COMPLETED
    ).count()
    
    today_conversions = ConversionHistory.objects.filter(
        created_at__date=now.date()
    ).count()
    
    # Популярные форматы конвертации
    popular_input_formats = ConversionHistory.objects.values('input_format').annotate(
        count=Count('input_format')
    ).order_by('-count')[:5]
    
    popular_output_formats = ConversionHistory.objects.values('output_format').annotate(
        count=Count('output_format')
    ).order_by('-count')[:5]
    
    # Средняя статистика
    avg_processing_time = ConversionHistory.objects.filter(
        status=ConversionHistory.STATUS_COMPLETED
    ).aggregate(avg_time=Avg('processing_time'))['avg_time'] or 0
    
    success_rate = 0
    if total_conversions > 0:
        success_rate = round((successful_conversions / total_conversions) * 100, 1)
    
    # Недавние конвертации с пагинацией
    from django.core.paginator import Paginator
    
    paginator = Paginator(queryset, 20)  # 20 элементов на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Общий размер обработанных данных
    from django.db import models
    total_data_processed = ConversionHistory.objects.aggregate(
        total_size=models.Sum('file_size')
    )['total_size'] or 0
    
    context = {
        'total_conversions': total_conversions,
        'successful_conversions': successful_conversions,
        'today_conversions': today_conversions,
        'total_data_processed': total_data_processed,
        'recent_conversions': page_obj,
        'popular_formats': {
            'input': popular_input_formats,
            'output': popular_output_formats
        },
        'system_stats': {
            'uptime': 'N/A',  # Это можно вычислить отдельно
            'avg_processing_time': round(avg_processing_time, 2),
            'success_rate': success_rate
        },
        # Параметры фильтрации для сохранения состояния формы
        'filters': {
            'file_type': file_type_filter,
            'status': status_filter,
            'search': search_query,
            'period': period_filter
        }
    }
    
    # Обработка AJAX-запросов для экспорта и очистки истории
    if request.method == 'DELETE':
        if request.user.is_staff:  # Только для администраторов
            ConversionHistory.objects.all().delete()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    return render(request, 'converter/conversion_history.html', context)


# Utility functions for adapter system integration
def get_adapter_info():
    """
    Get information about available adapters and their capabilities.
    """
    if not ADAPTERS_AVAILABLE or not engine_manager:
        return {
            'available': False,
            'engines': {},
            'error': 'Adapter system not available'
        }
    
    try:
        engines_info = {}
        
        # Get info for each engine type
        engine_types = ['video', 'image', 'audio', 'document', 'archive']
        
        for engine_type in engine_types:
            try:
                engine = engine_manager.get_engine(engine_type)
                if engine:
                    engines_info[engine_type] = {
                        'available': engine.is_available(),
                        'supported_formats': engine.get_supported_formats(),
                        'dependencies': engine.check_dependencies()
                    }
            except Exception as e:
                engines_info[engine_type] = {
                    'available': False,
                    'error': str(e)
                }
        
        return {
            'available': True,
            'engines': engines_info
        }
        
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }


def is_adapter_available(adapter_type):
    """
    Check if a specific adapter type is available.
    """
    if not ADAPTERS_AVAILABLE or not engine_manager:
        return False
    
    try:
        engine = engine_manager.get_engine(adapter_type)
        return engine and engine.is_available()
    except:
        return False
