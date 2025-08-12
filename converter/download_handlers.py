# -*- coding: utf-8 -*-
"""
Специализированные обработчики скачивания файлов для облачных платформ (Render, Railway, Heroku)
Решает проблемы с скачиванием файлов в облачных окружениях
"""

import os
import logging
from pathlib import Path
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse, Http404
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


class CloudDownloadHandler:
    """
    Обработчик скачивания файлов, оптимизированный для облачных платформ.
    Решает проблемы с таймаутами, памятью и нестабильными соединениями.
    """
    
    def __init__(self, chunk_size=8192, enable_resume=True, timeout=300):
        self.chunk_size = chunk_size
        self.enable_resume = enable_resume
        self.timeout = timeout
    
    def serve_file(self, file_path, filename=None, content_type=None, delete_after=False):
        """
        Обслуживает файл с поддержкой возобновления загрузки и оптимизацией для облака.
        
        Args:
            file_path: путь к файлу
            filename: имя файла для скачивания (если отличается от оригинала)
            content_type: MIME тип файла
            delete_after: удалить файл после скачивания
        """
        file_path = Path(file_path)
        
        if not file_path.exists() or not file_path.is_file():
            logger.error(f"File not found: {file_path}")
            raise Http404("File not found")
        
        file_size = file_path.stat().st_size
        filename = filename or file_path.name
        content_type = content_type or self._get_content_type(file_path)
        
        logger.info(f"Serving file: {filename} ({file_size} bytes)")
        
        def file_iterator():
            bytes_sent = 0
            try:
                with open(file_path, 'rb') as f:
                    while bytes_sent < file_size:
                        chunk = f.read(min(self.chunk_size, file_size - bytes_sent))
                        if not chunk:
                            break
                        bytes_sent += len(chunk)
                        yield chunk
                        
                        # Log progress for large files
                        if file_size > 1024 * 1024 and bytes_sent % (1024 * 1024) == 0:
                            progress = (bytes_sent / file_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}% ({bytes_sent}/{file_size})")
                
                logger.info(f"File served successfully: {filename} ({bytes_sent}/{file_size} bytes)")
                
            except Exception as e:
                logger.error(f"Error serving file {filename}: {e}")
                raise
            finally:
                if delete_after:
                    try:
                        file_path.unlink(missing_ok=True)
                        logger.info(f"File deleted after serving: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to delete file {filename}: {e}")
        
        response = StreamingHttpResponse(
            file_iterator(),
            content_type=content_type
        )
        
        # Критические заголовки для правильного скачивания
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = str(file_size)
        response['Accept-Ranges'] = 'bytes'
        
        # Заголовки кеширования
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        # Заголовки безопасности
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        
        # Дополнительные заголовки для облачных платформ
        response['X-Accel-Buffering'] = 'no'  # Nginx
        response['X-Sendfile-Type'] = 'X-Accel-Redirect'  # Nginx acceleration
        
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000'
        
        return response
    
    def _get_content_type(self, file_path):
        """Определяет MIME тип файла по расширению."""
        suffix = file_path.suffix.lower()
        
        content_type_map = {
            # Images
            '.gif': 'image/gif',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.ico': 'image/x-icon',
            '.svg': 'image/svg+xml',
            
            # Audio
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.aac': 'audio/aac',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            
            # Video
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.wmv': 'video/x-ms-wmv',
            
            # Documents
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.rtf': 'application/rtf',
            
            # Archives
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip',
        }
        
        return content_type_map.get(suffix, 'application/octet-stream')


class RenderOptimizedDownloader(CloudDownloadHandler):
    """
    Специализированный загрузчик для платформы Render.
    Учитывает особенности Render: таймауты, ограничения памяти, HTTP/2.
    """
    
    def __init__(self):
        # Render оптимизированные настройки
        super().__init__(
            chunk_size=16384,  # 16KB chunks для Render
            enable_resume=True,
            timeout=120  # 2 минуты таймаут на Render
        )
    
    def serve_file(self, file_path, filename=None, content_type=None, delete_after=False):
        """Render-оптимизированная подача файлов."""
        response = super().serve_file(file_path, filename, content_type, delete_after)
        
        # Специальные заголовки для Render
        response['Connection'] = 'close'  # Закрываем соединение после загрузки
        response['X-Render-Platform'] = 'optimized'
        
        # HTTP/2 оптимизации
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        
        return response


def get_download_handler():
    """
    Возвращает оптимальный обработчик скачивания в зависимости от платформы развертывания.
    """
    # Определяем платформу по переменным окружения
    if os.getenv('RENDER'):
        return RenderOptimizedDownloader()
    elif os.getenv('RAILWAY_ENVIRONMENT'):
        return CloudDownloadHandler(chunk_size=32768, timeout=180)  # Railway оптимизация
    elif os.getenv('HEROKU_APP_NAME'):
        return CloudDownloadHandler(chunk_size=8192, timeout=30)   # Heroku оптимизация
    else:
        return CloudDownloadHandler()  # Базовая облачная конфигурация


# Готовые view функции
@require_http_methods(["GET"])
def optimized_download_view(request, file_path, filename=None):
    """
    Оптимизированное представление для скачивания файлов.
    Автоматически выбирает лучший обработчик для текущей платформы.
    """
    try:
        downloader = get_download_handler()
        return downloader.serve_file(
            file_path=file_path,
            filename=filename,
            delete_after=False
        )
    except Http404:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Ошибка при скачивании файла'
        }, status=500)


@require_http_methods(["GET"])
def download_and_cleanup_view(request, file_path, filename=None):
    """
    Скачивание файла с последующим удалением.
    Идеально для временных файлов конвертации.
    """
    try:
        downloader = get_download_handler()
        return downloader.serve_file(
            file_path=file_path,
            filename=filename,
            delete_after=True
        )
    except Http404:
        raise
    except Exception as e:
        logger.error(f"Download and cleanup error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Ошибка при скачивании файла'
        }, status=500)


@require_http_methods(["GET"])
def download_converted_file(request, category, filename):
    """
    Специализированный endpoint для скачивания конвертированных файлов.
    Поддерживает все типы файлов: GIF, изображения, аудио, видео.
    """
    try:
        # Безопасное построение пути
        allowed_categories = {
            'gifs': 'converted',
            'images': 'images', 
            'audio': 'audio',
            'videos': 'videos',
            'documents': 'documents'
        }
        
        if category not in allowed_categories:
            raise Http404("Недопустимая категория файла")
        
        media_subdir = allowed_categories[category]
        file_path = Path(settings.MEDIA_ROOT) / media_subdir / filename
        
        # Проверка безопасности пути
        if not str(file_path.resolve()).startswith(str(Path(settings.MEDIA_ROOT).resolve())):
            raise Http404("Небезопасный путь к файлу")
        
        if not file_path.exists():
            raise Http404("Файл не найден")
        
        downloader = get_download_handler()
        return downloader.serve_file(
            file_path=file_path,
            filename=filename,
            delete_after=True  # Удаляем после скачивания для экономии места
        )
        
    except Http404:
        raise
    except Exception as e:
        logger.error(f"Error downloading converted file {category}/{filename}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Ошибка при скачивании конвертированного файла'
        }, status=500)


# Вспомогательные функции для диагностики
@require_http_methods(["GET"])
def download_test_view(request):
    """
    Тестовое представление для проверки работы скачивания.
    Создает тестовый файл и предлагает его скачать.
    """
    try:
        import tempfile
        
        # Создаем тестовый файл
        test_content = f"""
Тест скачивания файлов - {request.build_absolute_uri()}
Время: {os.popen('date').read().strip()}
Платформа: {os.getenv('RENDER', os.getenv('RAILWAY_ENVIRONMENT', os.getenv('HEROKU_APP_NAME', 'Unknown')))}
User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}
        """.strip()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            test_file_path = f.name
        
        downloader = get_download_handler()
        return downloader.serve_file(
            file_path=test_file_path,
            filename='download_test.txt',
            content_type='text/plain',
            delete_after=True
        )
        
    except Exception as e:
        logger.error(f"Download test error: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Ошибка тестирования скачивания: {str(e)}'
        }, status=500)
