from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
import os
import json
import tempfile
import zipfile
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from .models import ConversionTask
from .tasks import process_conversion_task
from .utils import get_file_type, validate_conversion_parameters

logger = logging.getLogger(__name__)
@csrf_exempt
@require_http_methods(["POST"])
def submit_conversion_task(request):
    """
    API endpoint для отправки задачи конвертации.
    Принимает файл и параметры конвертации, создает задачу и запускает Celery task.
    """
    try:
        # Валидация данных
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'Файл не найден'}, status=400)
        
        uploaded_file = request.FILES['file']
        source_format = request.POST.get('source_format')
        target_format = request.POST.get('target_format')
        
        if not source_format or not target_format:
            return JsonResponse({'error': 'Не указаны форматы конвертации'}, status=400)
        
        # Парсим параметры конвертации
        try:
            conversion_params = json.loads(request.POST.get('params', '{}'))
        except json.JSONDecodeError:
            conversion_params = {}
        
        # Валидация параметров
        validation_error = validate_conversion_parameters(source_format, target_format, conversion_params)
        if validation_error:
            return JsonResponse({'error': validation_error}, status=400)
        
        # Определяем тип файла
        file_type = get_file_type(uploaded_file.name)
        if file_type != source_format:
            return JsonResponse({
                'error': f'Тип файла ({file_type}) не соответствует указанному источнику ({source_format})'
            }, status=400)
        
        # Сохраняем файл
        file_path = default_storage.save(
            f'uploads/{uploaded_file.name}',
            uploaded_file
        )
        
        # Создаем задачу конвертации
        task = ConversionTask.objects.create(
            status=ConversionTask.STATUS_QUEUED,
            progress=0
        )
        
        # Устанавливаем метаданные
        task.set_metadata(
            original_filename=uploaded_file.name,
            source_format=source_format,
            target_format=target_format,
            conversion_params=conversion_params,
            file_path=file_path,
            file_size=uploaded_file.size,
            created_by=request.user.id if request.user.is_authenticated else None
        )
        task.save()
        
        # Запускаем Celery задачу
        try:
            celery_task = process_conversion_task.delay(task.id)
            task.set_metadata(celery_task_id=celery_task.id)
            task.save()
            
            logger.info(f"Создана задача конвертации {task.id} для файла {uploaded_file.name}")
            
            return JsonResponse({
                'success': True,
                'task_id': task.id,
                'message': 'Задача создана и отправлена на обработку',
                'estimated_time': estimate_processing_time(source_format, target_format, uploaded_file.size)
            })
            
        except Exception as e:
            # Если не удалось запустить Celery задачу, помечаем задачу как неудачную
            task.fail(f"Ошибка запуска обработки: {str(e)}")
            logger.error(f"Ошибка запуска Celery задачи: {str(e)}")
            return JsonResponse({'error': 'Ошибка запуска обработки'}, status=500)
            
    except Exception as e:
        logger.error(f"Ошибка создания задачи конвертации: {str(e)}")
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)


@require_http_methods(["GET"])
def get_task_queue(request):
    """
    API endpoint для получения текущей очереди задач конвертации.
    Возвращает список всех активных и недавних задач.
    """
    try:
        # Получаем задачи за последние 24 часа или все активные
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        tasks = ConversionTask.objects.filter(
            Q(created_at__gte=cutoff_time) | 
            Q(status__in=[ConversionTask.STATUS_QUEUED, ConversionTask.STATUS_RUNNING])
        ).order_by('-created_at')[:100]  # Ограничиваем до 100 задач
        
        # Сериализуем данные
        tasks_data = []
        for task in tasks:
            task_data = {
                'id': task.id,
                'status': task.status,
                'progress': task.progress,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'error_message': task.error_message,
                'filename': task.get_metadata('original_filename', 'Неизвестный файл'),
                'source_format': task.get_metadata('source_format', ''),
                'target_format': task.get_metadata('target_format', ''),
                'file_size': task.get_metadata('file_size', 0),
            }
            
            # Добавляем время выполнения для завершенных задач
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                task_data['duration'] = duration
            
            tasks_data.append(task_data)
        
        # Статистика очереди
        queue_stats = {
            'total': tasks.count(),
            'queued': tasks.filter(status=ConversionTask.STATUS_QUEUED).count(),
            'running': tasks.filter(status=ConversionTask.STATUS_RUNNING).count(),
            'completed': tasks.filter(status=ConversionTask.STATUS_DONE).count(),
            'failed': tasks.filter(status=ConversionTask.STATUS_FAILED).count(),
        }
        
        return JsonResponse({
            'success': True,
            'tasks': tasks_data,
            'stats': queue_stats,
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения очереди: {str(e)}")
        return JsonResponse({'error': 'Ошибка загрузки очереди'}, status=500)


@require_http_methods(["GET"])
def get_conversion_results(request):
    """
    API endpoint для получения результатов конвертации.
    Поддерживает фильтрацию и пагинацию.
    """
    try:
        # Получаем параметры фильтрации
        status_filter = request.GET.get('status')
        format_filter = request.GET.get('format')
        search_query = request.GET.get('search', '').strip()
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))
        
        # Базовый запрос - показываем задачи за последнюю неделю
        cutoff_time = timezone.now() - timedelta(days=7)
        queryset = ConversionTask.objects.filter(created_at__gte=cutoff_time)
        
        # Применяем фильтры
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if format_filter:
            queryset = queryset.filter(task_metadata__source_format=format_filter)
        
        if search_query:
            queryset = queryset.filter(
                Q(task_metadata__original_filename__icontains=search_query) |
                Q(task_metadata__converted_filename__icontains=search_query)
            )
        
        # Сортировка и пагинация
        queryset = queryset.order_by('-created_at')
        total_count = queryset.count()
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        tasks = queryset[start_index:end_index]
        
        # Сериализация результатов
        results = []
        for task in tasks:
            result_data = {
                'id': task.id,
                'status': task.status,
                'progress': task.progress,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'error_message': task.error_message,
                'original_filename': task.get_metadata('original_filename', ''),
                'converted_filename': task.get_metadata('converted_filename', ''),
                'source_format': task.get_metadata('source_format', ''),
                'target_format': task.get_metadata('target_format', ''),
                'file_size': task.get_metadata('file_size', 0),
                'output_size': task.get_metadata('output_size', 0),
            }
            
            # Добавляем URL'ы для скачивания (только для завершенных задач)
            if task.status == ConversionTask.STATUS_DONE:
                output_path = task.get_metadata('output_path')
                if output_path and default_storage.exists(output_path):
                    result_data['output_url'] = default_storage.url(output_path)
                    
                # Добавляем превью для изображений и GIF
                preview_path = task.get_metadata('preview_path')
                if preview_path and default_storage.exists(preview_path):
                    result_data['preview_url'] = default_storage.url(preview_path)
            
            results.append(result_data)
        
        # Статистика результатов
        stats = {
            'total': total_count,
            'completed': queryset.filter(status=ConversionTask.STATUS_DONE).count(),
            'processing': queryset.filter(
                status__in=[ConversionTask.STATUS_QUEUED, ConversionTask.STATUS_RUNNING]
            ).count(),
            'failed': queryset.filter(status=ConversionTask.STATUS_FAILED).count(),
        }
        
        # Метаданные пагинации
        pagination = {
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'has_next': end_index < total_count,
            'has_previous': page > 1,
        }
        
        return JsonResponse({
            'success': True,
            'results': results,
            'stats': stats,
            'pagination': pagination,
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения результатов: {str(e)}")
        return JsonResponse({'error': 'Ошибка загрузки результатов'}, status=500)


@require_http_methods(["GET"])
def get_task_status(request, task_id):
    """
    API endpoint для получения статуса конкретной задачи.
    Используется для polling обновлений прогресса.
    """
    try:
        task = get_object_or_404(ConversionTask, id=task_id)
        
        response_data = {
            'success': True,
            'task': {
                'id': task.id,
                'status': task.status,
                'progress': task.progress,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'error_message': task.error_message,
                'original_filename': task.get_metadata('original_filename', ''),
                'source_format': task.get_metadata('source_format', ''),
                'target_format': task.get_metadata('target_format', ''),
            }
        }
        
        # Добавляем дополнительные данные для завершенных задач
        if task.status == ConversionTask.STATUS_DONE:
            output_path = task.get_metadata('output_path')
            if output_path and default_storage.exists(output_path):
                response_data['task']['output_url'] = default_storage.url(output_path)
                response_data['task']['converted_filename'] = task.get_metadata('converted_filename', '')
                response_data['task']['output_size'] = task.get_metadata('output_size', 0)
        
        return JsonResponse(response_data)
        
    except ConversionTask.DoesNotExist:
        return JsonResponse({'error': 'Задача не найдена'}, status=404)
    except Exception as e:
        logger.error(f"Ошибка получения статуса задачи {task_id}: {str(e)}")
        return JsonResponse({'error': 'Ошибка загрузки статуса'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def download_batch_results(request):
    """
    API endpoint для создания zip-архива с несколькими результатами.
    """
    try:
        data = json.loads(request.body)
        result_ids = data.get('result_ids', [])
        
        if not result_ids:
            return JsonResponse({'error': 'Не указаны ID результатов'}, status=400)
        
        # Получаем завершенные задачи
        tasks = ConversionTask.objects.filter(
            id__in=result_ids,
            status=ConversionTask.STATUS_DONE
        )
        
        if not tasks.exists():
            return JsonResponse({'error': 'Нет доступных для скачивания файлов'}, status=400)
        
        # Создаем временный zip файл
        temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for task in tasks:
                output_path = task.get_metadata('output_path')
                if output_path and default_storage.exists(output_path):
                    # Читаем файл из storage
                    with default_storage.open(output_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Добавляем в архив с понятным именем
                    filename = task.get_metadata('converted_filename') or f"file_{task.id}"
                    zip_file.writestr(filename, file_content)
        
        # Сохраняем архив в storage
        archive_filename = f"batch_download_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
        with open(temp_zip.name, 'rb') as temp_file:
            archive_path = default_storage.save(f'downloads/{archive_filename}', temp_file)
        
        # Удаляем временный файл
        os.unlink(temp_zip.name)
        
        download_url = default_storage.url(archive_path)
        
        return JsonResponse({
            'success': True,
            'download_url': download_url,
            'archive_name': archive_filename,
            'files_count': tasks.count()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        logger.error(f"Ошибка создания batch архива: {str(e)}")
        return JsonResponse({'error': 'Ошибка создания архива'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_completed_tasks(request):
    """
    API endpoint для очистки завершенных задач.
    Удаляет задачи со статусом DONE старше 24 часов.
    """
    try:
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # Находим старые завершенные задачи
        old_completed_tasks = ConversionTask.objects.filter(
            status=ConversionTask.STATUS_DONE,
            completed_at__lt=cutoff_time
        )
        
        deleted_count = 0
        
        # Удаляем файлы и задачи
        for task in old_completed_tasks:
            try:
                # Удаляем связанные файлы
                file_path = task.get_metadata('file_path')
                output_path = task.get_metadata('output_path')
                preview_path = task.get_metadata('preview_path')
                
                for path in [file_path, output_path, preview_path]:
                    if path and default_storage.exists(path):
                        default_storage.delete(path)
                
                # Удаляем задачу
                task.delete()
                deleted_count += 1
                
            except Exception as e:
                logger.warning(f"Ошибка удаления задачи {task.id}: {str(e)}")
                continue
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Удалено {deleted_count} завершенных задач'
        })
        
    except Exception as e:
        logger.error(f"Ошибка очистки завершенных задач: {str(e)}")
        return JsonResponse({'error': 'Ошибка очистки задач'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_conversion_result(request, result_id):
    """
    API endpoint для удаления конкретного результата конвертации.
    """
    try:
        task = get_object_or_404(ConversionTask, id=result_id)
        
        # Удаляем связанные файлы
        file_path = task.get_metadata('file_path')
        output_path = task.get_metadata('output_path')
        preview_path = task.get_metadata('preview_path')
        
        for path in [file_path, output_path, preview_path]:
            if path and default_storage.exists(path):
                try:
                    default_storage.delete(path)
                except Exception as e:
                    logger.warning(f"Не удалось удалить файл {path}: {str(e)}")
        
        # Удаляем задачу
        task.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Результат успешно удален'
        })
        
    except ConversionTask.DoesNotExist:
        return JsonResponse({'error': 'Результат не найден'}, status=404)
    except Exception as e:
        logger.error(f"Ошибка удаления результата {result_id}: {str(e)}")
        return JsonResponse({'error': 'Ошибка удаления'}, status=500)


def estimate_processing_time(source_format, target_format, file_size):
    """
    Оценка времени обработки файла на основе его типа и размера.
    Возвращает примерное время в секундах.
    """
    # Базовые коэффициенты времени обработки (секунды на МБ)
    processing_rates = {
        ('video', 'gif'): 2.0,      # Видео в GIF - самое медленное
        ('video', 'mp4'): 0.5,      # Видео в видео - быстро
        ('image', 'jpg'): 0.1,      # Изображения - очень быстро
        ('image', 'png'): 0.2,
        ('image', 'webp'): 0.15,
        ('audio', 'mp3'): 0.3,      # Аудио - средне
        ('document', 'pdf'): 0.2,   # Документы - быстро
    }
    
    # Размер файла в МБ
    size_mb = file_size / (1024 * 1024)
    
    # Получаем коэффициент для данной конвертации
    key = (source_format, target_format)
    rate = processing_rates.get(key, 1.0)  # По умолчанию 1 сек/МБ
    
    # Рассчитываем время с учетом минимального времени
    estimated_time = max(5, int(size_mb * rate))  # Минимум 5 секунд
    
    return estimated_time


@require_http_methods(["GET"])
def get_conversion_stats(request):
    """
    API endpoint для получения общей статистики конвертации.
    """
    try:
        # Статистика за последние 30 дней
        cutoff_time = timezone.now() - timedelta(days=30)
        
        total_tasks = ConversionTask.objects.filter(created_at__gte=cutoff_time)
        
        # Общие статистики
        stats = {
            'total_conversions': total_tasks.count(),
            'successful_conversions': total_tasks.filter(status=ConversionTask.STATUS_DONE).count(),
            'failed_conversions': total_tasks.filter(status=ConversionTask.STATUS_FAILED).count(),
            'currently_processing': ConversionTask.objects.filter(
                status__in=[ConversionTask.STATUS_QUEUED, ConversionTask.STATUS_RUNNING]
            ).count(),
        }
        
        # Статистика по типам конвертации
        conversion_types = total_tasks.values(
            'task_metadata__source_format',
            'task_metadata__target_format'
        ).annotate(count=Count('id')).order_by('-count')
        
        # Статистика по дням
        daily_stats = []
        for i in range(7):  # Последние 7 дней
            day = timezone.now().date() - timedelta(days=i)
            day_tasks = total_tasks.filter(created_at__date=day)
            daily_stats.append({
                'date': day.isoformat(),
                'total': day_tasks.count(),
                'completed': day_tasks.filter(status=ConversionTask.STATUS_DONE).count(),
                'failed': day_tasks.filter(status=ConversionTask.STATUS_FAILED).count(),
            })
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'conversion_types': list(conversion_types),
            'daily_stats': daily_stats,
            'period': '30 days',
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {str(e)}")
        return JsonResponse({'error': 'Ошибка загрузки статистики'}, status=500)
