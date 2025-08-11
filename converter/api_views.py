"""
API представления для управления задачами конвертации файлов.
Поддерживает создание задач через multipart/form-data и URL,
проверку статуса, получение результатов и пакетное скачивание.
"""

from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.paginator import Paginator
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.urls import reverse

import os
import json
import uuid
import zipfile
import tempfile
import logging
import requests
from urllib.parse import urlparse
from io import BytesIO

from .models import ConversionTask
from .utils import VideoConverter, save_converted_gif, cleanup_temp_files

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def create_task_view(request):
    """
    Создание новой задачи конвертации.
    Поддерживает как multipart/form-data, так и JSON с URL.
    
    POST /api/tasks/create/
    
    Multipart form:
    - file: файл для конвертации
    - format: целевой формат (gif, mp4, avi, etc.)
    - width: ширина (опционально)
    - fps: частота кадров (опционально)
    - start_time: время начала в секундах (опционально)  
    - end_time: время окончания в секундах (опционально)
    - quality: качество low/medium/high (опционально)
    - speed: скорость воспроизведения (опционально)
    - grayscale: черно-белое (true/false, опционально)
    - reverse: обратное воспроизведение (true/false, опционально)
    - boomerang: эффект бумеранга (true/false, опционально)
    
    JSON body:
    {
        "url": "http://example.com/video.mp4",
        "format": "gif", 
        "width": 480,
        "fps": 15,
        ...
    }
    
    Response:
    {
        "success": true,
        "task_id": "uuid",
        "status": "queued",
        "message": "Задача создана успешно"
    }
    """
    try:
        content_type = request.content_type or ''
        
        # Определяем тип запроса
        if content_type.startswith('multipart/form-data'):
            # Multipart запрос с файлом
            if 'file' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'Файл не найден в запросе'
                }, status=400)
                
            file_obj = request.FILES['file']
            source_type = 'file'
            source_url = None
            
        elif content_type.startswith('application/json'):
            # JSON запрос с URL
            try:
                data = json.loads(request.body)
                if 'url' not in data:
                    return JsonResponse({
                        'success': False,
                        'error': 'URL не найден в запросе'
                    }, status=400)
                    
                source_url = data['url']
                source_type = 'url'
                file_obj = None
                
                # Валидация URL
                parsed_url = urlparse(source_url)
                if parsed_url.scheme not in ['http', 'https']:
                    return JsonResponse({
                        'success': False,
                        'error': 'Поддерживаются только HTTP и HTTPS URL'
                    }, status=400)
                    
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'Неверный JSON формат'
                }, status=400)
                
        else:
            return JsonResponse({
                'success': False,
                'error': 'Неподдерживаемый тип контента. Используйте multipart/form-data или application/json'
            }, status=400)

        # Получаем параметры конвертации
        def get_param(key, default=None, param_type=str):
            if content_type.startswith('application/json'):
                value = data.get(key, default)
            else:
                value = request.POST.get(key, default)
                
            if value is None or value == '':
                return default
                
            try:
                if param_type is bool:
                    return str(value).lower() in ['true', '1', 'on', 'yes']
                elif param_type is int:
                    return int(value)
                elif param_type is float:
                    return float(value)
                else:
                    return str(value)
            except (ValueError, TypeError):
                return default

        # Параметры конвертации
        target_format = get_param('format', 'gif')
        width = get_param('width', None, int)
        fps = get_param('fps', 15, int)
        start_time = get_param('start_time', 0, int)
        end_time = get_param('end_time', None, int)
        quality = get_param('quality', 'medium')
        speed = get_param('speed', 1.0, float)
        grayscale = get_param('grayscale', False, bool)
        reverse = get_param('reverse', False, bool)
        boomerang = get_param('boomerang', False, bool)
        high_quality = get_param('high_quality', quality == 'high', bool)
        dither = get_param('dither', 'bayer')
        keep_original_size = get_param('keep_original_size', False, bool)

        # Создаем задачу
        task = ConversionTask.objects.create(
            status=ConversionTask.STATUS_QUEUED,
            progress=0
        )
        
        # Сохраняем метаданные
        metadata = {
            'source_type': source_type,
            'source_url': source_url,
            'target_format': target_format,
            'conversion_params': {
                'width': width,
                'fps': fps,
                'start_time': start_time,
                'end_time': end_time,
                'quality': quality,
                'speed': speed,
                'grayscale': grayscale,
                'reverse': reverse,
                'boomerang': boomerang,
                'high_quality': high_quality,
                'dither': dither,
                'keep_original_size': keep_original_size
            }
        }
        
        if file_obj:
            metadata['original_filename'] = file_obj.name
            metadata['file_size'] = file_obj.size
            metadata['content_type'] = file_obj.content_type
            
            # Сохраняем файл временно
            temp_input_path = os.path.join(
                settings.MEDIA_ROOT, 
                'temp', 
                f'task_{task.id}_{file_obj.name}'
            )
            os.makedirs(os.path.dirname(temp_input_path), exist_ok=True)
            
            with open(temp_input_path, 'wb') as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)
                    
            metadata['temp_input_path'] = temp_input_path
            
        task.set_metadata(**metadata)
        task.save()
        
        # Запускаем конвертацию асинхронно (в продакшене использовать Celery)
        _process_conversion_task(task.id)
        
        return JsonResponse({
            'success': True,
            'task_id': str(task.id),
            'status': task.status,
            'message': 'Задача создана и поставлена в очередь на выполнение',
            'api_urls': {
                'status': reverse('api_task_status', args=[task.id]),
                'result': reverse('api_task_result', args=[task.id]),
                'download': reverse('api_task_download', args=[task.id])
            }
        })
        
    except Exception as e:
        logger.error(f"Ошибка при создании задачи: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def task_status_view(request, task_id):
    """
    Получение статуса задачи конвертации.
    
    GET /api/tasks/<task_id>/status/
    
    Response:
    {
        "success": true,
        "task_id": "uuid",
        "status": "running|queued|done|failed",
        "progress": 45,
        "created_at": "2024-01-01T12:00:00Z",
        "started_at": "2024-01-01T12:00:05Z",
        "completed_at": null,
        "duration": 30.5,
        "error_message": "",
        "metadata": {...}
    }
    """
    try:
        task = get_object_or_404(ConversionTask, id=task_id)
        
        response_data = {
            'success': True,
            'task_id': str(task.id),
            'status': task.status,
            'progress': task.progress,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'error_message': task.error_message,
            'is_finished': task.is_finished,
            'is_active': task.is_active,
            'metadata': task.task_metadata
        }
        
        if task.duration:
            response_data['duration_seconds'] = task.duration.total_seconds()
            
        return JsonResponse(response_data)
        
    except ConversionTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Задача не найдена'
        }, status=404)
    except Exception as e:
        logger.error(f"Ошибка при получении статуса задачи {task_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def task_result_view(request, task_id):
    """
    Получение результата выполненной задачи.
    
    GET /api/tasks/<task_id>/result/
    
    Response для успешной задачи:
    {
        "success": true,
        "task_id": "uuid", 
        "status": "done",
        "result": {
            "output_url": "/media/results/task_123.gif",
            "download_url": "/api/tasks/123/download/",
            "file_size": 1024000,
            "format": "gif",
            "duration": 30.5
        }
    }
    
    Response для неуспешной задачи:
    {
        "success": false,
        "task_id": "uuid",
        "status": "failed",
        "error_message": "..."
    }
    """
    try:
        task = get_object_or_404(ConversionTask, id=task_id)
        
        if task.status == ConversionTask.STATUS_DONE:
            # Задача успешно завершена
            result_path = task.get_metadata('result_path')
            if result_path and os.path.exists(result_path):
                file_size = os.path.getsize(result_path)
                filename = os.path.basename(result_path)
                
                return JsonResponse({
                    'success': True,
                    'task_id': str(task.id),
                    'status': task.status,
                    'result': {
                        'output_url': f"{settings.MEDIA_URL}results/{filename}",
                        'download_url': reverse('api_task_download', args=[task.id]),
                        'filename': filename,
                        'file_size': file_size,
                        'format': task.get_metadata('target_format', 'unknown'),
                        'original_filename': task.get_metadata('original_filename', ''),
                        'conversion_params': task.get_metadata('conversion_params', {})
                    },
                    'completed_at': task.completed_at.isoformat(),
                    'duration_seconds': task.duration.total_seconds() if task.duration else None
                })
            else:
                return JsonResponse({
                    'success': False,
                    'task_id': str(task.id),
                    'status': task.status,
                    'error': 'Файл результата не найден'
                })
                
        elif task.status == ConversionTask.STATUS_FAILED:
            # Задача завершилась с ошибкой
            return JsonResponse({
                'success': False,
                'task_id': str(task.id),
                'status': task.status,
                'error_message': task.error_message,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            })
            
        else:
            # Задача еще не завершена
            return JsonResponse({
                'success': False,
                'task_id': str(task.id),
                'status': task.status,
                'message': 'Задача еще выполняется или находится в очереди',
                'progress': task.progress
            })
            
    except ConversionTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Задача не найдена'
        }, status=404)
    except Exception as e:
        logger.error(f"Ошибка при получении результата задачи {task_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def task_download_view(request, task_id):
    """
    Скачивание результата задачи конвертации.
    
    GET /api/tasks/<task_id>/download/
    
    Response: файл в бинарном виде с соответствующими заголовками
    """
    try:
        task = get_object_or_404(ConversionTask, id=task_id)
        
        if task.status != ConversionTask.STATUS_DONE:
            return JsonResponse({
                'success': False,
                'error': 'Задача еще не завершена или завершилась с ошибкой'
            }, status=400)
            
        result_path = task.get_metadata('result_path')
        if not result_path or not os.path.exists(result_path):
            return JsonResponse({
                'success': False, 
                'error': 'Файл результата не найден'
            }, status=404)
            
        # Определяем тип контента по расширению
        ext = os.path.splitext(result_path)[1].lower()
        content_types = {
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.avi': 'video/avi',
            '.mov': 'video/quicktime',
            '.webm': 'video/webm',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
        }
        content_type = content_types.get(ext, 'application/octet-stream')
        
        # Формируем имя файла для скачивания
        original_name = task.get_metadata('original_filename', 'converted')
        name_without_ext = os.path.splitext(original_name)[0]
        target_format = task.get_metadata('target_format', 'gif')
        download_filename = f"{name_without_ext}_converted.{target_format}"
        
        # Отправляем файл
        with open(result_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{download_filename}"'
            response['Content-Length'] = os.path.getsize(result_path)
            return response
            
    except ConversionTask.DoesNotExist:
        raise Http404('Задача не найдена')
    except Exception as e:
        logger.error(f"Ошибка при скачивании результата задачи {task_id}: {str(e)}")
        raise Http404('Ошибка при скачивании файла')


@require_http_methods(["GET"])
def tasks_list_view(request):
    """
    Получение списка задач с пагинацией и фильтрацией.
    
    GET /api/tasks/
    
    Query parameters:
    - page: номер страницы (по умолчанию 1)
    - per_page: количество на страницу (по умолчанию 20, максимум 100)
    - status: фильтр по статусу (queued|running|done|failed)
    - format: фильтр по целевому формату
    - order: сортировка (-created_at, created_at, -updated_at, updated_at)
    
    Response:
    {
        "success": true,
        "tasks": [...],
        "pagination": {
            "page": 1,
            "per_page": 20, 
            "total": 150,
            "pages": 8,
            "has_next": true,
            "has_previous": false
        }
    }
    """
    try:
        # Параметры пагинации
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 20)), 100)
        
        # Базовый queryset
        queryset = ConversionTask.objects.all()
        
        # Фильтрация
        status_filter = request.GET.get('status')
        if status_filter and status_filter in [choice[0] for choice in ConversionTask.STATUS_CHOICES]:
            queryset = queryset.filter(status=status_filter)
            
        format_filter = request.GET.get('format')
        if format_filter:
            queryset = queryset.filter(task_metadata__target_format=format_filter)
        
        # Сортировка
        order = request.GET.get('order', '-created_at')
        valid_orders = ['created_at', '-created_at', 'updated_at', '-updated_at', 'status', '-status']
        if order in valid_orders:
            queryset = queryset.order_by(order)
        else:
            queryset = queryset.order_by('-created_at')
            
        # Пагинация
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        # Формирование ответа
        tasks_data = []
        for task in page_obj:
            task_data = {
                'task_id': str(task.id),
                'status': task.status,
                'progress': task.progress,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error_message': task.error_message,
                'target_format': task.get_metadata('target_format'),
                'original_filename': task.get_metadata('original_filename'),
                'file_size': task.get_metadata('file_size'),
                'api_urls': {
                    'status': reverse('api_task_status', args=[task.id]),
                    'result': reverse('api_task_result', args=[task.id]),
                    'download': reverse('api_task_download', args=[task.id])
                }
            }
            
            if task.duration:
                task_data['duration_seconds'] = task.duration.total_seconds()
                
            tasks_data.append(task_data)
            
        return JsonResponse({
            'success': True,
            'tasks': tasks_data,
            'pagination': {
                'page': page_obj.number,
                'per_page': per_page,
                'total': paginator.count,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
        
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Некорректные параметры запроса'
        }, status=400)
    except Exception as e:
        logger.error(f"Ошибка при получении списка задач: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }, status=500)


@require_http_methods(["GET", "POST"])
def batch_download_view(request):
    """
    Пакетное скачивание результатов нескольких задач в ZIP архиве.
    
    GET /api/tasks/batch-download/?task_ids=1,2,3,4
    POST /api/tasks/batch-download/
    {
        "task_ids": [1, 2, 3, 4]
    }
    
    Response: ZIP файл с результатами всех успешных задач
    """
    try:
        # Получаем список ID задач
        if request.method == 'GET':
            task_ids_str = request.GET.get('task_ids', '')
            if not task_ids_str:
                return JsonResponse({
                    'success': False,
                    'error': 'Не указаны ID задач'
                }, status=400)
            try:
                task_ids = [int(x.strip()) for x in task_ids_str.split(',') if x.strip()]
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Некорректные ID задач'
                }, status=400)
                
        else:  # POST
            try:
                data = json.loads(request.body)
                task_ids = data.get('task_ids', [])
                if not isinstance(task_ids, list):
                    return JsonResponse({
                        'success': False,
                        'error': 'task_ids должен быть массивом'
                    }, status=400)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'Неверный JSON формат'
                }, status=400)
        
        if not task_ids:
            return JsonResponse({
                'success': False,
                'error': 'Список задач пуст'
            }, status=400)
            
        if len(task_ids) > 50:  # Ограничение на количество задач
            return JsonResponse({
                'success': False,
                'error': 'Слишком много задач (максимум 50)'
            }, status=400)
        
        # Получаем успешные задачи
        successful_tasks = ConversionTask.objects.filter(
            id__in=task_ids,
            status=ConversionTask.STATUS_DONE
        )
        
        if not successful_tasks.exists():
            return JsonResponse({
                'success': False,
                'error': 'Нет успешно завершенных задач для скачивания'
            }, status=400)
        
        # Создаем ZIP архив в памяти
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            added_files = set()  # Для избежания дубликатов имен файлов
            
            for task in successful_tasks:
                result_path = task.get_metadata('result_path')
                if not result_path or not os.path.exists(result_path):
                    continue
                    
                # Формируем уникальное имя файла в архиве
                original_name = task.get_metadata('original_filename', 'converted')
                name_without_ext = os.path.splitext(original_name)[0]
                target_format = task.get_metadata('target_format', 'gif')
                
                base_filename = f"task_{task.id}_{name_without_ext}.{target_format}"
                filename = base_filename
                counter = 1
                
                # Обеспечиваем уникальность имен
                while filename in added_files:
                    name_part = f"task_{task.id}_{name_without_ext}_{counter}"
                    filename = f"{name_part}.{target_format}"
                    counter += 1
                
                added_files.add(filename)
                
                # Добавляем файл в архив
                zip_file.write(result_path, filename)
        
        if not added_files:
            return JsonResponse({
                'success': False,
                'error': 'Нет доступных файлов для скачивания'
            }, status=400)
        
        # Подготавливаем ответ
        zip_buffer.seek(0)
        zip_data = zip_buffer.getvalue()
        
        # Формируем имя ZIP файла
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"conversion_results_{timestamp}.zip"
        
        response = HttpResponse(zip_data, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        response['Content-Length'] = len(zip_data)
        
        # Добавляем метаданные в заголовки
        response['X-Total-Tasks'] = str(len(task_ids))
        response['X-Successful-Tasks'] = str(len(added_files))
        response['X-Files-Count'] = str(len(added_files))
        
        return response
        
    except Exception as e:
        logger.error(f"Ошибка при пакетном скачивании: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }, status=500)


def _process_conversion_task(task_id):
    """
    Обработка задачи конвертации.
    В продакшене должна быть заменена на Celery задачу.
    """
    import threading
    
    def worker():
        try:
            task = ConversionTask.objects.get(id=task_id)
            task.start()
            
            # Получаем параметры
            source_type = task.get_metadata('source_type')
            conversion_params = task.get_metadata('conversion_params', {})
            
            # Подготавливаем входной файл
            if source_type == 'url':
                source_url = task.get_metadata('source_url')
                task.update_progress(10)
                
                # Скачиваем файл по URL
                response = requests.get(source_url, stream=True)
                response.raise_for_status()
                
                filename = os.path.basename(urlparse(source_url).path) or 'downloaded_file'
                temp_input_path = os.path.join(
                    settings.MEDIA_ROOT,
                    'temp',
                    f'task_{task.id}_{filename}'
                )
                os.makedirs(os.path.dirname(temp_input_path), exist_ok=True)
                
                with open(temp_input_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                task.set_metadata(temp_input_path=temp_input_path, original_filename=filename)
                task.save()
                
            else:
                temp_input_path = task.get_metadata('temp_input_path')
            
            task.update_progress(20)
            
            # Создаем конвертер
            converter = VideoConverter(use_moviepy=True)
            
            # Создаем путь для результата
            target_format = task.get_metadata('target_format', 'gif')
            result_filename = f'task_{task.id}_result.{target_format}'
            result_path = os.path.join(settings.MEDIA_ROOT, 'results', result_filename)
            os.makedirs(os.path.dirname(result_path), exist_ok=True)
            
            task.update_progress(30)
            
            # Выполняем конвертацию
            if target_format == 'gif':
                success = converter.convert_video_to_gif(
                    temp_input_path,
                    result_path,
                    **conversion_params
                )
            else:
                # Для других форматов можно добавить соответствующие методы
                success = False
                
            if success and os.path.exists(result_path):
                task.set_metadata(result_path=result_path)
                task.save()
                task.complete()
            else:
                task.fail('Ошибка при конвертации файла')
                
        except Exception as e:
            logger.error(f"Ошибка при обработке задачи {task_id}: {str(e)}")
            task.fail(str(e))
            
        finally:
            # Очистка временных файлов
            temp_path = task.get_metadata('temp_input_path')
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    
    # Запускаем в отдельном потоке (в продакшене использовать Celery)
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
