"""
Примеры view-функций с использованием новых адаптеров.
Демонстрация интеграции слоя адаптеров с Django views.
"""

import tempfile
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .adapters import engine_manager, VideoEngine
from .utils import save_converted_gif, cleanup_temp_files

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def convert_with_adapters_view(request):
    """
    Конвертация файлов с использованием нового слоя адаптеров.
    Универсальная функция для обработки различных типов файлов.
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'Файл не найден'
            })
        
        input_file = request.FILES['file']
        
        # Получаем параметры конвертации
        output_format = request.POST.get('output_format', 'gif')
        engine_type = request.POST.get('engine_type')  # Опционально
        
        # Дополнительные параметры (для видео)
        conversion_params = {
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
        
        # Очищаем None значения
        conversion_params = {k: v for k, v in conversion_params.items() 
                           if v is not None and v != '' and v != 'None'}
        
        # Создаем временный файл для результата
        with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as temp_output:
            temp_output_path = temp_output.name
        
        try:
            # Выполняем конвертацию через менеджер адаптеров
            result = engine_manager.convert_file(
                input_file=input_file,
                output_path=temp_output_path,
                engine_type=engine_type,
                **conversion_params
            )
            
            if result.success:
                # Для GIF файлов используем существующую логику сохранения
                if output_format.lower() == 'gif':
                    gif_url = save_converted_gif(temp_output_path, input_file.name)
                    if gif_url:
                        return JsonResponse({
                            'success': True,
                            'output_url': gif_url,
                            'metadata': result.metadata,
                            'message': 'Конвертация завершена успешно!'
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'error': 'Ошибка при сохранении результата'
                        })
                else:
                    # Для других форматов можно добавить свою логику сохранения
                    return JsonResponse({
                        'success': True,
                        'output_path': result.output_path,
                        'metadata': result.metadata,
                        'message': 'Конвертация завершена успешно!'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.error_message
                })
                
        finally:
            # Очищаем временные файлы
            cleanup_temp_files([temp_output_path])
            
    except Exception as e:
        logger.error(f"Ошибка при конвертации через адаптеры: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def video_convert_adapter_view(request):
    """
    Специализированная конвертация видео с использованием VideoEngine.
    Демонстрирует прямое использование конкретного адаптера.
    """
    try:
        if 'video' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'Видеофайл не найден'
            })
        
        video_file = request.FILES['video']
        
        # Получаем параметры
        use_moviepy = request.POST.get('use_moviepy', 'true').lower() == 'true'
        
        # Создаем адаптер видео напрямую
        video_engine = VideoEngine(use_moviepy=use_moviepy)
        
        # Проверяем доступность
        if not video_engine.is_available():
            deps = video_engine.check_dependencies()
            return JsonResponse({
                'success': False,
                'error': f'Видео адаптер недоступен. Статус зависимостей: {deps}'
            })
        
        # Получаем информацию о видео
        video_info = video_engine.get_video_info(video_file)
        
        # Параметры конвертации
        conversion_params = {
            'width': request.POST.get('width'),
            'fps': int(request.POST.get('fps', 15)),
            'start_time': int(request.POST.get('start_time', 0)),
            'end_time': request.POST.get('end_time'),
            'keep_original_size': request.POST.get('keep_original_size') in ['true', 'on', '1'],
        }
        
        # Очищаем None значения
        conversion_params = {k: v for k, v in conversion_params.items() 
                           if v is not None and v != '' and v != 'None'}
        
        # Создаем временный файл для GIF
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_gif:
            temp_gif_path = temp_gif.name
        
        try:
            # Выполняем конвертацию
            result = video_engine.convert(
                input_file=video_file,
                output_path=temp_gif_path,
                **conversion_params
            )
            
            if result.success:
                # Сохраняем GIF
                gif_url = save_converted_gif(temp_gif_path, video_file.name)
                if gif_url:
                    return JsonResponse({
                        'success': True,
                        'gif_url': gif_url,
                        'video_info': video_info,
                        'conversion_metadata': result.metadata,
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
                    'error': result.error_message
                })
                
        finally:
            cleanup_temp_files([temp_gif_path])
            
    except Exception as e:
        logger.error(f"Ошибка при конвертации видео через адаптер: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка: {str(e)}'
        })


def engine_status_view(request):
    """
    Возвращает статус всех адаптеров конвертации.
    """
    try:
        status = engine_manager.get_engine_status()
        supported_formats = engine_manager.get_supported_formats()
        
        return JsonResponse({
            'success': True,
            'engines_status': status,
            'supported_formats': supported_formats,
        })
        
    except Exception as e:
        logger.error(f"Ошибка при получении статуса адаптеров: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка: {str(e)}'
        })


def detect_file_type_view(request):
    """
    Определяет тип файла для выбора подходящего адаптера.
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'Файл не найден'
            })
        
        file = request.FILES['file']
        engine_type = engine_manager.detect_engine_type(file.name)
        
        if engine_type:
            # Получаем адаптер и его информацию
            engine = engine_manager.get_engine(engine_type)
            if engine:
                supported_formats = engine.get_supported_formats()
                dependencies = engine.check_dependencies()
                
                return JsonResponse({
                    'success': True,
                    'engine_type': engine_type,
                    'supported_formats': supported_formats,
                    'dependencies': dependencies,
                    'available': engine.is_available()
                })
        
        return JsonResponse({
            'success': False,
            'error': 'Не удалось определить тип файла'
        })
        
    except Exception as e:
        logger.error(f"Ошибка при определении типа файла: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка: {str(e)}'
        })


# Демонстрация обратной совместимости - обертка для существующих views
def legacy_video_convert_view(request):
    """
    Обертка для обеспечения обратной совместимости.
    Использует новый VideoEngine, но сохраняет старый интерфейс.
    """
    try:
        if request.method == 'POST' and 'video' in request.FILES:
            video_file = request.FILES['video']
            
            # Создаем VideoEngine с настройками по умолчанию
            video_engine = VideoEngine(use_moviepy=True)
            
            # Создаем временный GIF файл
            with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_gif:
                temp_gif_path = temp_gif.name
            
            try:
                # Базовые параметры конвертации
                result = video_engine.convert(
                    input_file=video_file,
                    output_path=temp_gif_path,
                    width=480,
                    fps=15
                )
                
                if result.success:
                    gif_url = save_converted_gif(temp_gif_path, video_file.name)
                    if gif_url:
                        return JsonResponse({
                            'success': True,
                            'gif_url': gif_url,
                            'message': 'Конвертация завершена успешно!'
                        })
                
                return JsonResponse({
                    'success': False,
                    'error': result.error_message if result else 'Неизвестная ошибка'
                })
                
            finally:
                cleanup_temp_files([temp_gif_path])
        
        return JsonResponse({
            'success': False,
            'error': 'Неверный запрос'
        })
        
    except Exception as e:
        logger.error(f"Ошибка в legacy view: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка: {str(e)}'
        })
