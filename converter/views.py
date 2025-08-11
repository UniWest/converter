from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
import tempfile
import json
import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path

# Дополнительные импорты для мониторинга системы
try:
    import psutil
except ImportError:
    psutil = None

# Импорты для аудиообработки
try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

# Импортируем формы из корня проекта
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from forms import VideoUploadForm, VideoProcessingForm

# Импортируем утилиты для конвертации
from .utils import VideoConverter, save_uploaded_video, save_converted_gif, cleanup_temp_files

logger = logging.getLogger(__name__)


def home_view(request):
    """
    Главная страница с формой для загрузки видео.
    """
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Получаем настройки из формы
                settings_data = form.get_conversion_settings()
                video_file = settings_data['video_file']
                
                # Создаем конвертер (используем FFmpeg для скорости)
                converter = VideoConverter(use_moviepy=False)
                
                # Создаем временный файл для GIF
                with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_gif:
                    temp_gif_path = temp_gif.name
                
                # Выполняем конвертацию
                success = converter.convert_video_to_gif(
                    video_file,
                    temp_gif_path,
                    width=settings_data['width'],
                    fps=settings_data['fps'],
                    start_time=settings_data['start_time'],
                    end_time=settings_data['end_time'],
                    keep_original_size=settings_data['keep_original_size']
                )
                
                if success and os.path.exists(temp_gif_path):
                    # Сохраняем GIF в медиа папку
                    gif_url = save_converted_gif(temp_gif_path, video_file.name)
                    
                    if gif_url:
                        messages.success(request, 'Видео успешно конвертировано в GIF!')
                        return render(request, 'converter/success.html', {
                            'gif_url': gif_url,
                            'original_filename': video_file.name
                        })
                    else:
                        messages.error(request, 'Ошибка при сохранении GIF файла')
                else:
                    messages.error(request, 'Ошибка при конвертации видео')
                    
            except Exception as e:
                logger.error(f"Ошибка при конвертации: {str(e)}")
                messages.error(request, f'Произошла ошибка: {str(e)}')
            
            finally:
                # Очищаем временные файлы
                cleanup_temp_files([temp_gif_path] if 'temp_gif_path' in locals() else [])
        
        else:
            # Если форма невалидна, показываем ошибки
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = VideoUploadForm()
    
    return render(request, 'converter/home.html', {'form': form})


def convert_video_view(request):
    """
    Обработка конвертации видео в GIF.
    """
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Получаем настройки из формы
                settings_data = form.get_conversion_settings()
                video_file = settings_data['video_file']
                
                # Создаем конвертер (пробуем сначала MoviePy, потом FFmpeg)
                converter = VideoConverter(use_moviepy=True)
                
                # Создаем временный файл для GIF
                with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_gif:
                    temp_gif_path = temp_gif.name
                
                # Выполняем конвертацию
                success = converter.convert_video_to_gif(
                    video_file,
                    temp_gif_path,
                    width=settings_data['width'],
                    fps=settings_data['fps'],
                    start_time=settings_data['start_time'],
                    end_time=settings_data['end_time']
                )
                
                if success and os.path.exists(temp_gif_path):
                    # Сохраняем GIF в медиа папку
                    gif_url = save_converted_gif(temp_gif_path, video_file.name)
                    
                    if gif_url:
                        messages.success(request, 'Видео успешно конвертировано в GIF!')
                        return render(request, 'converter/success.html', {
                            'gif_url': gif_url,
                            'original_filename': video_file.name
                        })
                    else:
                        messages.error(request, 'Ошибка при сохранении GIF файла')
                else:
                    messages.error(request, 'Ошибка при конвертации видео')
                    
            except Exception as e:
                logger.error(f"Ошибка при конвертации: {str(e)}")
                messages.error(request, f'Произошла ошибка: {str(e)}')
            
            finally:
                # Очищаем временные файлы
                cleanup_temp_files([temp_gif_path] if 'temp_gif_path' in locals() else [])
        
        else:
            # Если форма невалидна, возвращаемся на главную
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    
    return redirect('converter:home')


def conversion_interface(request):
    """
    Новый интерфейс для выбора типов конвертации и пакетной загрузки.
    """
    return render(request, 'converter/conversion_interface.html')


def conversion_results(request):
    """
    Страница результатов конвертации с галереей и статистикой.
    """
    context = {
        'total_files': 0,
        'completed_files': 0,
        'processing_files': 0,
        'failed_files': 0,
    }
    return render(request, 'converter/results.html', context)


def quick_convert_view(request):
    """
    Быстрая конвертация с предустановленными настройками.
    """
    if request.method == 'POST':
        form = VideoProcessingForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                video_file = form.cleaned_data['video']
                quality_settings = form.get_quality_settings()
                
                # Создаем конвертер
                converter = VideoConverter(use_moviepy=True)
                
                # Создаем временный файл для GIF
                with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_gif:
                    temp_gif_path = temp_gif.name
                
                # Выполняем конвертацию с предустановленными настройками
                success = converter.convert_video_to_gif(
                    video_file,
                    temp_gif_path,
                    width=quality_settings.get('width', 480),
                    fps=quality_settings.get('fps', 15),
                    start_time=0,
                    end_time=None
                )
                
                if success and os.path.exists(temp_gif_path):
                    gif_url = save_converted_gif(temp_gif_path, video_file.name)
                    
                    if gif_url:
                        return JsonResponse({
                            'success': True,
                            'gif_url': gif_url,
                            'message': 'Конвертация завершена успешно!'
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
                    
            except Exception as e:
                logger.error(f"Ошибка при быстрой конвертации: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Произошла ошибка: {str(e)}'
                })
            
            finally:
                cleanup_temp_files([temp_gif_path] if 'temp_gif_path' in locals() else [])
        else:
            return JsonResponse({
                'success': False,
                'error': 'Некорректные данные формы',
                'form_errors': form.errors
            })
    else:
        form = VideoProcessingForm()
        return render(request, 'converter/quick_convert.html', {'form': form})


@csrf_exempt
@require_http_methods(["POST"])
def ajax_convert_view(request):
    """
    AJAX конвертация видео для асинхронной обработки.
    """
    try:
        if 'video' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'Видеофайл не найден'
            })
        
        video_file = request.FILES['video']
        
        # Получаем параметры из POST данных
        width = request.POST.get('width')
        width = int(width) if width not in (None, '', 'None') else None
        fps = int(request.POST.get('fps', 15))
        start_time = int(request.POST.get('start_time', 0))
        end_time = request.POST.get('end_time')
        end_time = int(end_time) if end_time else None
        keep_original_size = request.POST.get('keep_original_size') in ['true', 'on', '1']
        speed = float(request.POST.get('speed', '1.0') or 1.0)
        grayscale = request.POST.get('grayscale') in ['true', 'on', '1']
        reverse = request.POST.get('reverse') in ['true', 'on', '1']
        boomerang = request.POST.get('boomerang') in ['true', 'on', '1']
        high_quality = request.POST.get('high_quality') in ['true', 'on', '1']
        dither = request.POST.get('dither') or 'bayer'
        
        # Базовая валидация
        if video_file.size > 500 * 1024 * 1024:  # 500 МБ
            return JsonResponse({
                'success': False,
                'error': 'Файл слишком большой (максимум 500 МБ)'
            })
        
        # Создаем конвертер
        converter = VideoConverter(use_moviepy=True)
        
        # Получаем информацию о видео
        video_info = converter.get_video_info(video_file)
        
        # Создаем временный файл для GIF
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_gif:
            temp_gif_path = temp_gif.name
        
        # Выполняем конвертацию
        success = converter.convert_video_to_gif(
            video_file,
            temp_gif_path,
            width=width,
            fps=fps,
            start_time=start_time,
            end_time=end_time,
            keep_original_size=keep_original_size,
            speed=speed,
            grayscale=grayscale,
            reverse=reverse,
            boomerang=boomerang,
            high_quality=high_quality,
            dither=dither
        )
        
        if success and os.path.exists(temp_gif_path):
            gif_url = save_converted_gif(temp_gif_path, video_file.name)
            
            if gif_url:
                return JsonResponse({
                    'success': True,
                    'gif_url': gif_url,
                    'video_info': video_info,
                    'message': 'Конвертация завершена успешно!'
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
            
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Некорректные параметры: {str(e)}'
        })
    except Exception as e:
        logger.error(f"Ошибка при AJAX конвертации: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка: {str(e)}'
        })
    
    finally:
        cleanup_temp_files([temp_gif_path] if 'temp_gif_path' in locals() else [])


def video_info_view(request):
    """
    Получение информации о видео файле.
    """
    if request.method == 'POST' and 'video' in request.FILES:
        try:
            video_file = request.FILES['video']
            
            # Создаем конвертер для получения информации
            converter = VideoConverter()
            video_info = converter.get_video_info(video_file)
            
            if video_info:
                return JsonResponse({
                    'success': True,
                    'info': video_info
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Не удалось получить информацию о видео'
                })
                
        except Exception as e:
            logger.error(f"Ошибка при получении информации о видео: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Произошла ошибка: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Видеофайл не найден'
    })


def download_gif_view(request, filename):
    """
    Скачивание конвертированного GIF файла.
    """
    try:
        gif_path = os.path.join(settings.MEDIA_ROOT, 'gifs', filename)
        
        if os.path.exists(gif_path):
            with open(gif_path, 'rb') as gif_file:
                response = HttpResponse(gif_file.read(), content_type='image/gif')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
        else:
            raise Http404('GIF файл не найден')
            
    except Exception as e:
        logger.error(f"Ошибка при скачивании GIF: {str(e)}")
        raise Http404('Ошибка при скачивании файла')


def converter_status_view(request):
    """
    Расширенная проверка статуса конвертера с информацией о версиях и доступности бинарников.
    """
    import subprocess
    import platform
    import psutil
    from datetime import datetime
    from pathlib import Path
    
    try:
        converter = VideoConverter()
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'architecture': platform.architecture()[0]
            },
            'resources': {
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available,
                'disk_usage': {
                    'total': psutil.disk_usage('.').total,
                    'free': psutil.disk_usage('.').free,
                    'used': psutil.disk_usage('.').used
                }
            },
            'engines': {},
            'binaries': {},
            'media_paths': {}
        }
        
        # Проверка MoviePy
        moviepy_info = {
            'available': False,
            'version': None,
            'path': None,
            'status': 'not_found'
        }
        
        try:
            import moviepy
            moviepy_info.update({
                'available': True,
                'version': getattr(moviepy, '__version__', 'unknown'),
                'path': moviepy.__file__,
                'status': 'available'
            })
        except ImportError:
            moviepy_info['status'] = 'not_installed'
        except Exception as e:
            moviepy_info['status'] = f'error: {str(e)}'
        
        status_data['engines']['moviepy'] = moviepy_info
        
        # Проверка FFmpeg
        ffmpeg_path = getattr(settings, 'FFMPEG_BINARY', 'ffmpeg')
        ffmpeg_info = {
            'available': False,
            'version': None,
            'path': ffmpeg_path,
            'status': 'not_found',
            'executable': False
        }
        
        try:
            # Проверяем доступность FFmpeg
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Извлекаем версию из вывода
                output_lines = result.stdout.split('\n')
                version_line = next((line for line in output_lines if 'ffmpeg version' in line.lower()), '')
                
                if version_line:
                    version = version_line.split(' ')[2] if len(version_line.split(' ')) > 2 else 'unknown'
                else:
                    version = 'detected'
                
                ffmpeg_info.update({
                    'available': True,
                    'version': version,
                    'executable': True,
                    'status': 'available'
                })
            else:
                ffmpeg_info['status'] = f'execution_error: {result.stderr}'
                
        except FileNotFoundError:
            ffmpeg_info['status'] = 'binary_not_found'
        except subprocess.TimeoutExpired:
            ffmpeg_info['status'] = 'timeout'
        except Exception as e:
            ffmpeg_info['status'] = f'error: {str(e)}'
        
        status_data['engines']['ffmpeg'] = ffmpeg_info
        
        # Дополнительные бинарники
        additional_binaries = {
            'ffprobe': getattr(settings, 'FFPROBE_BINARY', 'ffprobe'),
            'imagemagick': 'convert',
            'gifsicle': 'gifsicle'
        }
        
        for binary_name, binary_path in additional_binaries.items():
            binary_info = {
                'available': False,
                'version': None,
                'path': binary_path,
                'status': 'not_found'
            }
            
            try:
                if binary_name == 'ffprobe':
                    cmd = [binary_path, '-version']
                elif binary_name == 'imagemagick':
                    cmd = [binary_path, '-version']
                elif binary_name == 'gifsicle':
                    cmd = [binary_path, '--version']
                else:
                    cmd = [binary_path, '--version']
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    version_output = result.stdout or result.stderr
                    version_line = version_output.split('\n')[0] if version_output else 'detected'
                    
                    binary_info.update({
                        'available': True,
                        'version': version_line.strip(),
                        'status': 'available'
                    })
                else:
                    binary_info['status'] = 'execution_error'
                    
            except FileNotFoundError:
                binary_info['status'] = 'binary_not_found'
            except subprocess.TimeoutExpired:
                binary_info['status'] = 'timeout'
            except Exception as e:
                binary_info['status'] = f'error: {str(e)}'
            
            status_data['binaries'][binary_name] = binary_info
        
        # Информация о медиа путях
        media_root = Path(settings.MEDIA_ROOT)
        status_data['media_paths'] = {
            'media_root': str(media_root),
            'media_root_exists': media_root.exists(),
            'gifs_dir': str(media_root / 'gifs'),
            'gifs_dir_exists': (media_root / 'gifs').exists(),
            'uploads_dir': str(media_root / 'uploads'),
            'uploads_dir_exists': (media_root / 'uploads').exists(),
            'temp_dir': str(Path(settings.BASE_DIR) / 'temp'),
            'temp_dir_exists': (Path(settings.BASE_DIR) / 'temp').exists()
        }
        
        # Статистика файлов
        try:
            from .models import ConversionTask
            
            total_tasks = ConversionTask.objects.count()
            status_data['statistics'] = {
                'total_tasks': total_tasks,
                'queued_tasks': ConversionTask.objects.filter(status=ConversionTask.STATUS_QUEUED).count(),
                'running_tasks': ConversionTask.objects.filter(status=ConversionTask.STATUS_RUNNING).count(),
                'completed_tasks': ConversionTask.objects.filter(status=ConversionTask.STATUS_DONE).count(),
                'failed_tasks': ConversionTask.objects.filter(status=ConversionTask.STATUS_FAILED).count()
            }
            
            # Размеры файлов в медиа директории
            def get_dir_size(path):
                if not path.exists():
                    return 0
                return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
            
            status_data['storage'] = {
                'gifs_size': get_dir_size(media_root / 'gifs'),
                'uploads_size': get_dir_size(media_root / 'uploads'),
                'temp_size': get_dir_size(Path(settings.BASE_DIR) / 'temp')
            }
            
        except Exception as e:
            status_data['statistics'] = {'error': str(e)}
            status_data['storage'] = {'error': str(e)}
        
        # Рекомендуемый движок
        if moviepy_info['available'] and ffmpeg_info['available']:
            recommended_engine = 'MoviePy (с поддержкой FFmpeg)'
        elif moviepy_info['available']:
            recommended_engine = 'MoviePy'
        elif ffmpeg_info['available']:
            recommended_engine = 'FFmpeg'
        else:
            recommended_engine = 'Недоступен'
        
        status_data['recommended_engine'] = recommended_engine
        status_data['status'] = 'healthy' if (moviepy_info['available'] or ffmpeg_info['available']) else 'critical'
        
        return JsonResponse(status_data)
        
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': f'Ошибка при получении статуса системы: {str(e)}'
        })


def test_gif_view(request, filename):
    """
    Тестовое представление для диагностики GIF файлов.
    """
    try:
        import os
        gif_path = os.path.join(settings.MEDIA_ROOT, 'gifs', filename)
        
        if os.path.exists(gif_path):
            with open(gif_path, 'rb') as gif_file:
                response = HttpResponse(gif_file.read(), content_type='image/gif')
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                return response
        else:
            return HttpResponse(f'Файл {filename} не найден по пути: {gif_path}', status=404)
            
    except Exception as e:
        return HttpResponse(f'Ошибка: {str(e)}', status=500)


# =============================
# Speech-to-Text (распознавание речи)
# =============================
# Импорты уже определены выше
from converter_site.tasks import perform_speech_recognition


def _ensure_temp_dir() -> Path:
    tmp = Path(settings.BASE_DIR) / 'temp'
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp


def audio_to_text_page(request):
    """
    Страница с UI для распознавания речи из аудио.
    """
    return render(request, 'converter/audio_to_text.html')


@csrf_exempt
@require_http_methods(["POST"])
def audio_to_text_api(request):
    """
    Расширенный API для распознавания речи из аудиофайлов.
    
    Поддерживает:
    - Множественные движки распознавания (Whisper, Google, Yandex, Vosk)
    - Различные языки и качество обработки
    - Выходные форматы (TXT, SRT, JSON)
    - Временные метки и определение спикеров
    - Асинхронная обработка больших файлов
    """
    try:
        if 'audio' not in request.FILES:
            return JsonResponse({
                'success': False, 
                'error': 'Аудиофайл не найден (поле audio)'
            }, status=400)

        audio_file = request.FILES['audio']

        # Валидация размера файла
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 500 * 1024 * 1024)
        if audio_file.size and audio_file.size > max_size:
            return JsonResponse({
                'success': False, 
                'error': f'Файл слишком большой. Максимальный размер: {max_size // (1024*1024)} МБ'
            }, status=400)

        # Валидация типа файла
        allowed_types = [
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/wave', 'audio/x-wav',
            'audio/m4a', 'audio/x-m4a', 'audio/aac', 'audio/ogg', 'audio/flac',
            'audio/wma', 'audio/webm'
        ]
        
        allowed_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma']
        
        is_valid_type = (
            audio_file.content_type in allowed_types or 
            any(audio_file.name.lower().endswith(ext) for ext in allowed_extensions)
        )
        
        if not is_valid_type:
            return JsonResponse({
                'success': False,
                'error': 'Неподдерживаемый формат файла. Поддерживаются: MP3, WAV, M4A, AAC, OGG, FLAC, WMA'
            }, status=400)

        # Получаем параметры из запроса
        engine = request.POST.get('engine', 'whisper')  # whisper|google|yandex|vosk
        language = request.POST.get('language', 'ru-RU')
        quality = request.POST.get('quality', 'standard')  # standard|high|fast
        output_format = request.POST.get('output_format', 'text')  # text|srt|json
        include_timestamps = request.POST.get('include_timestamps', 'false').lower() in ['true', '1', 'on']
        detect_speakers = request.POST.get('detect_speakers', 'false').lower() in ['true', '1', 'on']
        enhance_speech = request.POST.get('enhance_speech', 'false').lower() in ['true', '1', 'on']
        remove_silence = request.POST.get('remove_silence', 'false').lower() in ['true', '1', 'on']

        # Логируем запрос
        logger.info(
            f"STT запрос: файл={audio_file.name}, размер={audio_file.size}, "
            f"движок={engine}, язык={language}, качество={quality}, формат={output_format}"
        )

        # Сохраняем файл во временную директорию
        temp_dir = _ensure_temp_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        src_path = temp_dir / f"upload_{timestamp}_{audio_file.name}"
        
        try:
            with open(src_path, 'wb') as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)

            # Определяем способ обработки в зависимости от размера и сложности
            audio_duration = _get_audio_duration(src_path)
            
            # Для больших файлов или сложных настроек используем асинхронную обработку
            # Пока отключим асинхронную обработку для отладки
            should_use_async = (
                audio_duration > 300 or  # Больше 5 минут
                remove_silence or
                detect_speakers
                # Убираем engine == 'whisper' из условий async, чтобы короткие файлы обрабатывались синхронно
            )
            
            if should_use_async:
                # Асинхронная обработка через Celery (если доступен)
                from converter_site.tasks import convert_audio_to_text
                
                options = {
                    'language': language,
                    'quality': quality,
                    'output_format': output_format,
                    'include_timestamps': include_timestamps,
                    'detect_speakers': detect_speakers,
                    'enhance_speech': enhance_speech,
                    'remove_silence': remove_silence,
                    'engine': engine
                }
                
                # Проверяем доступность Celery
                try:
                    # Попытка использовать Celery
                    task = convert_audio_to_text.delay(str(src_path), options)
                    
                    return JsonResponse({
                        'success': True,
                        'async': True,
                        'task_id': task.id,
                        'status': 'processing',
                        'estimated_time': max(30, int(audio_duration * 0.1)),
                        'check_status_url': f'/api/task-status/{task.id}/',
                        'message': 'Файл добавлен в очередь на обработку. Используйте task_id для проверки статуса.'
                    })
                except AttributeError:
                    # Celery недоступен, переходим к синхронной обработке
                    logger.info("Celery недоступен, выполняется синхронная обработка")
                    should_use_async = False
                    
            if not should_use_async:
                # Синхронная обработка для небольших файлов или если Celery недоступен
                logger.info(f"Синхронная обработка файла: {audio_duration:.1f} сек, движок: {engine}")
                result = _process_audio_sync(src_path, {
                    'language': language,
                    'quality': quality,
                    'output_format': output_format,
                    'include_timestamps': include_timestamps,
                    'enhance_speech': enhance_speech,
                    'engine': engine,
                    'duration': audio_duration  # Передаем длительность
                })
                
                return JsonResponse({
                    'success': True,
                    'async': False,
                    'text': result['text'],
                    'metadata': {
                        'duration': result.get('duration'),
                        'language': result.get('language'),
                        'engine_used': result.get('engine_used', engine),
                        'processing_time': result.get('processing_time'),
                        'confidence': result.get('confidence')
                    },
                    'segments': result.get('segments', []) if include_timestamps else None
                })
        
        finally:
            # Очистка временных файлов для синхронной обработки
            if not should_use_async:
                try:
                    src_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {src_path}: {e}")

    except Exception as e:
        logger.error(f"Ошибка API STT: {e}", exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': f'Ошибка обработки: {str(e)}'
        }, status=500)


def _get_audio_duration(file_path: Path) -> float:
    """
    Получает длительность аудиофайла в секундах.
    """
    try:
        if AudioSegment is None:
            logger.warning("pydub недоступен, возвращаем длительность по умолчанию")
            return 60.0  # возвращаем значение по умолчанию
        
        audio_segment = AudioSegment.from_file(str(file_path))
        return len(audio_segment) / 1000.0  # конвертируем из мс в с
    except Exception as e:
        logger.warning(f"Не удалось определить длительность аудио: {e}")
        return 60.0  # возвращаем значение по умолчанию


def _process_long_audio_google(audio_segment: AudioSegment, language: str, quality: str, temp_dir: Path) -> str:
    """
    Обработка длинных аудиофайлов для Google Speech Recognition.
    Делит аудио на сегменты по 45 секунд с перекрытием для надежности.
    """
    total_duration = len(audio_segment) / 1000.0
    logger.info(f"Обработка длинного аудио: {total_duration:.1f} сек")
    
    # Используем 45 секунд вместо 50 для большой безопасности
    segment_length_ms = 45 * 1000  # 45 секунд в мс
    overlap_ms = 5 * 1000  # 5 секунд перекрытия
    segments_text = []
    processed_segments = 0
    success_segments = 0
    
    # Предобработка аудио для лучшего распознавания
    processed_audio = audio_segment
    
    # Нормализация громкости
    try:
        processed_audio = processed_audio.normalize()
        logger.info("Применена нормализация громкости")
    except Exception as e:
        logger.warning(f"Не удалось применить нормализацию: {e}")
    
    # Конвертируем в моно 16 кГц для оптимального распознавания
    if processed_audio.channels > 1:
        processed_audio = processed_audio.set_channels(1)
        logger.info("Конвертация в моно")
    
    if processed_audio.frame_rate != 16000:
        processed_audio = processed_audio.set_frame_rate(16000)
        logger.info(f"Конвертация частоты с {audio_segment.frame_rate} до 16000 Гц")
    
    # Сегментация с перекрытием
    for i in range(0, len(processed_audio), segment_length_ms - overlap_ms):
        segment_start = i
        segment_end = min(i + segment_length_ms, len(processed_audio))
        segment = processed_audio[segment_start:segment_end]
        
        # Пропускаем слишком короткие сегменты
        if len(segment) < 3000:  # Меньше 3 секунд
            logger.debug(f"Пропуск слишком короткого сегмента: {len(segment)/1000:.1f}с")
            continue
        
        processed_segments += 1
        segment_number = processed_segments
        segment_duration = len(segment) / 1000.0
        
        logger.info(f"Обработка сегмента {segment_number}: {segment_duration:.1f}с ({segment_start/1000:.1f}s - {segment_end/1000:.1f}s)")
        
        # Сохраняем сегмент во временный файл
        segment_path = temp_dir / f"long_segment_{segment_number:03d}.wav"
        
        try:
            # Экспортируем с оптимальными параметрами
            segment.export(
                str(segment_path), 
                format='wav',
                parameters=["-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le"]
            )
            
            # Распознавание с повторными попытками
            segment_text = None
            max_attempts = 3
            
            for attempt in range(max_attempts):
                try:
                    segment_text = perform_speech_recognition(str(segment_path), language, quality)
                    if segment_text and segment_text.strip():
                        break
                    else:
                        logger.warning(f"Попытка {attempt + 1}: пустой результат")
                except Exception as e:
                    logger.warning(f"Попытка {attempt + 1} не удалась: {e}")
                    if attempt == max_attempts - 1:
                        raise
                    
                # Небольшая пауза между попытками
                import time
                time.sleep(1)
            
            if segment_text and segment_text.strip():
                # Очистка текста
                cleaned_text = segment_text.strip()
                
                # Убираем дубликаты с предыдущим сегментом (из-за перекрытия)
                if segments_text and len(segments_text) > 0:
                    last_text = segments_text[-1]
                    # Проверяем перекрытие по последним словам
                    last_words = last_text.split()[-3:] if last_text else []
                    current_words = cleaned_text.split()[:3] if cleaned_text else []
                    
                    # Если есть перекрытие слов, убираем их
                    if last_words and current_words:
                        overlap_count = 0
                        for word in last_words:
                            if word.lower() in [w.lower() for w in current_words]:
                                overlap_count += 1
                        
                        if overlap_count >= 2:  # Если 2+ слов повторяются
                            # Убираем первые overlap_count слов
                            words_to_keep = cleaned_text.split()[overlap_count:]
                            cleaned_text = ' '.join(words_to_keep)
                            logger.debug(f"Удалено перекрытие: {overlap_count} слов")
                
                if cleaned_text:  # Добавляем только непустой текст
                    segments_text.append(cleaned_text)
                    success_segments += 1
                    logger.info(f"Успешно сегмент {segment_number} ({len(cleaned_text)} симв.): '{cleaned_text[:60]}...'")
                else:
                    logger.warning(f"Пустой текст после очистки сегмента {segment_number}")
            else:
                logger.warning(f"Не удалось распознать сегмент {segment_number}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки сегмента {segment_number}: {e}")
        finally:
            # Удаляем временный файл
            try:
                if segment_path.exists():
                    segment_path.unlink()
            except Exception as e:
                logger.debug(f"Не удалось удалить {segment_path}: {e}")
    
    # Объединяем все сегменты
    if segments_text:
        # Окончательная очистка текста
        full_text = ' '.join(segments_text)
        # Убираем лишние пробелы и нормализуем
        full_text = ' '.join(full_text.split())
        
        logger.info(
            f"Обработка завершена: {processed_segments} сегментов, "
            f"{success_segments} успешных, {len(full_text)} символов"
        )
        return full_text
    else:
        logger.error("Не удалось распознать ни одного сегмента")
        return ""


def _process_audio_sync(file_path: Path, options: dict) -> dict:
    """
    Синхронная обработка аудиофайла для небольших файлов.
    """
    from datetime import datetime
    
    start_time = datetime.now()
    temp_dir = _ensure_temp_dir()
    wav_path = None
    
    try:
        # Проверяем доступность pydub
        if AudioSegment is None:
            logger.warning("pydub недоступен, используем файл как есть")
            # Пробуем обработать файл напрямую
            language = options.get('language', 'ru-RU')
            quality = options.get('quality', 'standard')
            text = perform_speech_recognition(str(file_path), language, quality)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'text': text,
                'duration': 60.0,  # по умолчанию
                'language': language,
                'engine_used': 'google',
                'processing_time': processing_time,
                'confidence': 0.9
            }
        
        # Конвертируем в WAV 16kHz mono
        audio_segment = AudioSegment.from_file(str(file_path))
        duration = len(audio_segment) / 1000.0
        
        # Предобработка аудио
        processed_audio = audio_segment
        
        if processed_audio.channels > 1:
            processed_audio = processed_audio.set_channels(1)
        
        if processed_audio.frame_rate != 16000:
            processed_audio = processed_audio.set_frame_rate(16000)
        
        if options.get('enhance_speech', False):
            processed_audio = processed_audio.normalize()
        
        # Сохраняем в WAV
        wav_path = temp_dir / f"{file_path.stem}_processed.wav"
        processed_audio.export(str(wav_path), format='wav')
        
        # Распознавание речи
        language = options.get('language', 'ru-RU')
        quality = options.get('quality', 'standard')
        engine = options.get('engine', 'google')
        
        # Используем выбранный движок
        if engine == 'whisper':
            # Проверяем доступность Whisper
            try:
                from faster_whisper import WhisperModel
                
                logger.info(f"Whisper доступен, обрабатываем файл {duration:.1f} сек")
                
                # Настройки Whisper - принудительно используем CPU
                model_name = 'base'  # Используем базовую модель
                device = 'cpu'  # Принудительно CPU вместо 'auto'
                compute_type = 'int8'
                
                # Определяем язык
                if language.startswith('ru'):
                    whisper_language = 'ru'
                elif language.startswith('en'):
                    whisper_language = 'en'
                else:
                    whisper_language = None  # Автоопределение
                
                logger.info(f"Инициализация Whisper: модель={model_name}, устройство={device}, тип={compute_type}")
                
                # Загружаем модель Whisper с обработкой ошибок
                try:
                    model = WhisperModel(model_name, device=device, compute_type=compute_type)
                    logger.info("Модель Whisper успешно загружена")
                except Exception as model_error:
                    logger.error(f"Ошибка загрузки модели Whisper: {model_error}")
                    raise model_error
                
                # Транскрибируем с обработкой ошибок
                try:
                    logger.info(f"Начало транскрибации файла: {wav_path}")
                    segments_result, info = model.transcribe(
                        str(wav_path), 
                        language=whisper_language,
                        beam_size=5,
                        best_of=5,
                        temperature=0.0
                    )
                    
                    # Собираем текст с обработкой ошибок
                    text_segments = []
                    segment_count = 0
                    
                    for segment in segments_result:
                        if segment.text and segment.text.strip():
                            text_segments.append(segment.text.strip())
                            segment_count += 1
                    
                    text = ' '.join(text_segments)
                    actual_engine = 'whisper'
                    
                    logger.info(f"Whisper транскрибация завершена: {segment_count} сегментов, {len(text)} символов")
                    
                except Exception as transcribe_error:
                    logger.error(f"Ошибка транскрибации Whisper: {transcribe_error}")
                    raise transcribe_error
                
            except Exception as e:
                logger.warning(f"Whisper недоступен или ошибка ({e}), переключаемся на Google с сегментацией")
                if duration > 60:  # Длинные файлы - сегментация
                    text = _process_long_audio_google(processed_audio, language, quality, temp_dir)
                else:
                    text = perform_speech_recognition(str(wav_path), language, quality)
                actual_engine = 'google'
        else:
            # Используем Google как основной/fallback движок
            # Для длинных файлов (> 60 сек) делим на сегменты
            if duration > 60:  # Больше 1 минуты
                logger.info(f"Используем сегментацию для файла {duration:.1f} сек")
                text = _process_long_audio_google(processed_audio, language, quality, temp_dir)
            else:
                logger.info(f"Обработка короткого файла {duration:.1f} сек одним запросом")
                text = perform_speech_recognition(str(wav_path), language, quality)
            actual_engine = 'google'
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            'text': text,
            'duration': duration,
            'language': language,
            'engine_used': actual_engine,  # Используем реальный движок
            'processing_time': processing_time,
            'confidence': 0.9  # Примерная оценка
        }
        
        # Добавляем временные метки если нужно
        if options.get('include_timestamps', False):
            result['segments'] = [{
                'start': 0.0,
                'end': duration,
                'text': text,
                'confidence': 0.9
            }]
        
        return result
    
    finally:
        # Очищаем временные файлы
        if wav_path and wav_path.exists():
            try:
                wav_path.unlink()
            except Exception as e:
                logger.warning(f"Не удалось удалить {wav_path}: {e}")


@csrf_exempt
@require_http_methods(["GET"])
def task_status_api(request, task_id):
    """
    API для проверки статуса асинхронных задач.
    """
    try:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {
                'success': True,
                'status': 'pending',
                'message': 'Задача в очереди на выполнение',
                'progress': 0
            }
        
        elif task_result.state == 'PROGRESS':
            meta = task_result.info or {}
            response = {
                'success': True,
                'status': 'processing',
                'message': meta.get('status', 'Обработка...'),
                'progress': meta.get('progress', 0),
                'total': meta.get('total', 100)
            }
        
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            response = {
                'success': True,
                'status': 'completed',
                'message': 'Задача завершена',
                'progress': 100,
                'result': result
            }
        
        elif task_result.state == 'FAILURE':
            error_info = task_result.info or {}
            response = {
                'success': False,
                'status': 'failed',
                'message': 'Ошибка выполнения задачи',
                'error': error_info.get('error', str(task_result.traceback)) if hasattr(task_result, 'traceback') else 'Unknown error'
            }
        
        else:
            response = {
                'success': True,
                'status': task_result.state.lower(),
                'message': f'Задача в состоянии: {task_result.state}',
                'info': str(task_result.info) if task_result.info else None
            }
        
        response['task_id'] = task_id
        return JsonResponse(response)
    
    except Exception as e:
        logger.error(f"Ошибка проверки статуса задачи {task_id}: {e}")
        return JsonResponse({
            'success': False,
            'status': 'error',
            'error': f'Ошибка проверки статуса: {str(e)}',
            'task_id': task_id
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def cancel_task_api(request, task_id):
    """
    API для отмены асинхронной задачи.
    """
    try:
        from celery.result import AsyncResult
        from converter_site.tasks import app
        
        # Отменяем задачу
        app.control.revoke(task_id, terminate=True)
        
        # Проверяем статус
        task_result = AsyncResult(task_id)
        
        return JsonResponse({
            'success': True,
            'message': f'Задача {task_id} отменена',
            'task_id': task_id,
            'status': task_result.state.lower()
        })
    
    except Exception as e:
        logger.error(f"Ошибка отмены задачи {task_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Ошибка отмены задачи: {str(e)}',
            'task_id': task_id
        }, status=500)


# =============================
# Photos to GIF (создание GIF из фотографий)
# =============================

def photos_to_gif_page(request):
    """
    Страница с UI для создания GIF из фотографий.
    """
    return render(request, 'converter/photos_to_gif.html')


@csrf_exempt
@require_http_methods(["POST"])
def photos_to_gif_api(request):
    """
    API для создания GIF из загруженных фотографий.
    
    Поддерживает:
    - Загрузку множественных изображений
    - Настройку скорости анимации и размера
    - Эффекты перехода и оптимизацию
    - Различные параметры качества
    """
    try:
        # Проверяем наличие изображений
        if not request.FILES.getlist('images'):
            return JsonResponse({
                'success': False,
                'error': 'Не загружено ни одного изображения'
            }, status=400)
        
        photo_files = request.FILES.getlist('images')
        
        # Разрешаем минимум 1 изображение (если одно — продублируем кадр)
        if len(photo_files) < 1:
            return JsonResponse({
                'success': False,
                'error': 'At least 1 image is required to create a GIF'
            }, status=400)
        
        # Получаем параметры из POST данных
        frame_duration = float(request.POST.get('frame_duration', 0.5))  # в секундах
        output_size = request.POST.get('output_size', '480')
        colors = int(request.POST.get('colors', 128))
        loop_gif = request.POST.get('loop', 'true').lower() == 'true'
        sort_order = request.POST.get('sort_order', 'filename')
        pingpong = request.POST.get('pingpong', 'false').lower() == 'true'
        optimize = request.POST.get('optimize', 'true').lower() == 'true'
        
        # Базовая валидация
        if len(photo_files) > 100:
            return JsonResponse({
                'success': False,
                'error': 'Maximum 100 images allowed at once'
            }, status=400)
        
        # Проверяем общий размер файлов
        total_size = sum(photo.size for photo in photo_files)
        if total_size > 100 * 1024 * 1024:  # 100 МБ
            return JsonResponse({
                'success': False,
                'error': f'Total file size too large (max 100 MB). Current: {total_size/(1024*1024):.1f} MB'
            }, status=400)
        
        # Сортируем изображения если нужно
        if sort_order == 'filename':
            photo_files = sorted(photo_files, key=lambda x: x.name.lower())
        elif sort_order == 'reverse':
            photo_files = list(reversed(photo_files))
        # 'upload' оставляем как есть
        
        logger.info(f"Creating GIF from {len(photo_files)} images with parameters:")
        logger.info(f"Frame duration: {frame_duration}s, Size: {output_size}, Colors: {colors}")
        logger.info(f"Loop: {loop_gif}, Pingpong: {pingpong}, Optimize: {optimize}")
        
        # Создаем временный файл для GIF
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_gif:
            temp_gif_path = temp_gif.name
        
        try:
            # Создаем конвертер
            from .utils import PhotoToGifConverter
            converter = PhotoToGifConverter()
            
            # Подготавливаем параметры
            gif_params = {
                'duration': int(frame_duration * 1000),  # Конвертируем в миллисекунды
                'loop': 0 if loop_gif else 1,  # 0 = бесконечно
                'quality': 85,
                'optimize': optimize,
                'reverse': pingpong,  # pingpong эффект
            }
            
            # Настройка размера
            if output_size != 'original':
                target_width = int(output_size)
                # Для квадратного соотношения можно задать и высоту
                gif_params['resize'] = (target_width, target_width)
            
            # Если только одно изображение — продублируем его, чтобы сформировать анимацию из 2 кадров
            if len(photo_files) == 1:
                try:
                    single = photo_files[0]
                    # Считываем байты и создаем два независимых объекта файла
                    data = single.read()
                    try:
                        single.seek(0)
                    except Exception:
                        pass
                    photo_files = [
                        ContentFile(data, name=single.name),
                        ContentFile(data, name=single.name)
                    ]
                except Exception as e:
                    logger.warning(f"Failed to duplicate single image for GIF: {e}. Proceeding by referencing the same file twice.")
                    photo_files = [photo_files[0], photo_files[0]]

            # Создаем GIF
            success = converter.create_gif_from_photos(
                photo_files,
                temp_gif_path,
                **gif_params
            )
            
            if success and os.path.exists(temp_gif_path):
                # Сохраняем GIF в медиа папку
                original_name = f"{len(photo_files)}_photos"
                gif_url = save_converted_gif(temp_gif_path, f"{original_name}.gif")
                
                if gif_url:
                    # Получаем информацию о созданном файле
                    gif_size = os.path.getsize(temp_gif_path) if os.path.exists(temp_gif_path) else 0
                    
                    return JsonResponse({
                        'success': True,
                        'gif_url': gif_url,
                        'message': f'GIF successfully created from {len(photo_files)} images!',
'file_info': {
                            'frames': (len(photo_files) * 2 - 2) if pingpong and len(photo_files) > 1 else len(photo_files),
                            'duration_per_frame': frame_duration,
                            'total_duration': ((len(photo_files) * 2 - 2) if pingpong and len(photo_files) > 1 else len(photo_files)) * frame_duration,
                            'file_size': gif_size,
                            'dimensions': f"{output_size}x{output_size}" if output_size != 'original' else 'Original',
                            'colors': colors,
                            'optimized': optimize
                        }
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Error saving GIF file'
                    }, status=500)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Error creating GIF from images'
                }, status=500)
                
        finally:
            # Очищаем временные файлы
            cleanup_temp_files([temp_gif_path] if 'temp_gif_path' in locals() else [])
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid parameters: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in photos to GIF API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)


# =============================
# Engine Status Endpoint
# =============================

@require_http_methods(["GET"])
def engine_status(request):
    """
    Returns the status of all registered engines (AudioEngine, VideoEngine, etc.).
    Loops through registered engines, calls is_available() and check_dependencies(),
    and returns JSON with the status information.
    """
    try:
        # Import the engine manager and related adapters
        from .adapters import engine_manager
        
        if not engine_manager:
            return JsonResponse({
                'success': False,
                'error': 'Engine manager not available'
            }, status=503)
        
        # Get status of all engines using the engine manager
        engines_status = engine_manager.get_engine_status()
        
        # Add timestamp and basic system info
        from datetime import datetime
        import platform
        
        response_data = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'engines': engines_status,
            'system_info': {
                'platform': platform.platform(),
                'python_version': platform.python_version()
            }
        }
        
        # Add memory info if psutil is available
        try:
            import psutil
            response_data['system_info'].update({
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available
            })
        except ImportError:
            pass
        
        return JsonResponse(response_data)
        
    except ImportError:
        logger.error("Adapters not available")
        return JsonResponse({
            'success': False,
            'error': 'Adapter system not available'
        }, status=503)
    
    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        return JsonResponse({
            'success': False,
            'error': f'An error occurred while checking engine status: {str(e)}'
        }, status=500)
