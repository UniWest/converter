"""
Утилиты для конвертации видео в GIF.
Поддержка как MoviePy, так и прямого вызова FFmpeg.
"""

import os
import subprocess
import tempfile
import logging
import mimetypes
from pathlib import Path
from django.conf import settings

# PIL imports for image processing
try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageEnhance = None

logger = logging.getLogger(__name__)


def get_file_type(filename):
    """
    Определение типа файла по расширению.
    Возвращает категорию файла: video, image, audio, document.
    """
    if not filename:
        return None
    
    extension = os.path.splitext(filename.lower())[1]
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg']
    audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a']
    document_extensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.html', '.htm']
    
    if extension in video_extensions:
        return 'video'
    elif extension in image_extensions:
        return 'image'
    elif extension in audio_extensions:
        return 'audio'
    elif extension in document_extensions:
        return 'document'
    else:
        return None


def validate_conversion_parameters(source_format, target_format, params):
    """
    Валидация параметров конвертации.
    Возвращает сообщение об ошибке или None, если все OK.
    """
    # Проверяем поддерживаемые комбинации форматов
    supported_conversions = {
        'video': ['gif', 'mp4', 'webm', 'avi'],
        'image': ['jpg', 'png', 'webp', 'pdf'],
        'audio': ['mp3', 'wav', 'flac', 'ogg'],
        'document': ['pdf', 'docx', 'txt', 'html']
    }
    
    if source_format not in supported_conversions:
        return f'Неподдерживаемый исходный формат: {source_format}'
    
    if target_format not in supported_conversions[source_format]:
        return f'Неподдерживаемая конвертация {source_format} -> {target_format}'
    
    # Валидация специфичных параметров для видео -> GIF
    if source_format == 'video' and target_format == 'gif':
        width = params.get('width')
        fps = params.get('fps')
        
        if width and (not isinstance(width, int) or width < 144 or width > 1920):
            return 'Ширина должна быть между 144 и 1920 пикселями'
        
        if fps and (not isinstance(fps, int) or fps < 5 or fps > 30):
            return 'FPS должен быть между 5 и 30'
    
    return None


def get_mime_type(filename):
    """
    Получение MIME типа файла по имени.
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'


def format_file_size(size_bytes):
    """
    Форматирование размера файла в читаемый вид.
    """
    if size_bytes == 0:
        return '0 B'
    
    size_names = ['B', 'KB', 'MB', 'GB', 'TB']
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f'{s} {size_names[i]}'


def create_thumbnail(file_path, thumbnail_path, size=(300, 200)):
    """
    Создание миниатюры для предварительного просмотра.
    Работает с изображениями и видео.
    """
    try:
        file_type = get_file_type(file_path)
        
        if file_type == 'image':
            return _create_image_thumbnail(file_path, thumbnail_path, size)
        elif file_type == 'video':
            return _create_video_thumbnail(file_path, thumbnail_path, size)
        else:
            return False
    except Exception as e:
        logger.error(f'Ошибка создания миниатюры: {str(e)}')
        return False


def _create_image_thumbnail(image_path, thumbnail_path, size):
    """
    Создание миниатюры изображения.
    """
    try:
        from PIL import Image
        
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.LANCZOS)
            img.save(thumbnail_path, 'JPEG', quality=85)
        
        return True
    except ImportError:
        logger.warning('Pillow не установлен для создания миниатюр изображений')
        return False
    except Exception as e:
        logger.error(f'Ошибка создания миниатюры изображения: {str(e)}')
        return False


def _create_video_thumbnail(video_path, thumbnail_path, size):
    """
    Создание миниатюры видео (первый кадр).
    """
    try:
        from moviepy.editor import VideoFileClip
        
        with VideoFileClip(video_path) as clip:
            # Берем кадр на 1 секунде или в начале, если видео короче
            frame_time = min(1.0, clip.duration / 2)
            frame = clip.get_frame(frame_time)
            
            # Сохраняем как изображение
            from PIL import Image
            img = Image.fromarray(frame)
            img.thumbnail(size, Image.LANCZOS)
            img.save(thumbnail_path, 'JPEG', quality=85)
        
        return True
    except ImportError:
        logger.warning('MoviePy или Pillow не установлены для создания миниатюр видео')
        return False
    except Exception as e:
        logger.error(f'Ошибка создания миниатюры видео: {str(e)}')
        return False


class VideoConverter:
    """
    Класс для конвертации видео в GIF.
    Поддерживает использование MoviePy и FFmpeg.
    """
    
    def __init__(self, use_moviepy=True):
        self.use_moviepy = use_moviepy
        
    def convert_video_to_gif(self, video_file, output_path, **kwargs):
        """
        Основной метод для конвертации видео в GIF.
        
        Args:
            video_file: Загруженный файл видео
            output_path: Путь для сохранения GIF
            **kwargs: Дополнительные параметры конвертации
        
        Returns:
            bool: True если конвертация прошла успешно
        """
        try:
            if self.use_moviepy:
                return self._convert_with_moviepy(video_file, output_path, **kwargs)
            else:
                return self._convert_with_ffmpeg(video_file, output_path, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка при конвертации видео: {str(e)}")
            return False
    
    def _convert_with_moviepy(self, video_file, output_path, **kwargs):
        """
        Конвертация с использованием MoviePy.
        """
        temp_video_path = None
        clip = None
        
        try:
            try:
                from moviepy.editor import VideoFileClip
            except ImportError:
                # Fallback for newer MoviePy versions
                from moviepy import VideoFileClip
            
            # Сохраняем временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                for chunk in video_file.chunks():
                    temp_file.write(chunk)
                temp_file.flush()  # Очищаем буфер
                temp_video_path = temp_file.name
            
            # Проверяем, что файл закрыт
            import time
            time.sleep(0.1)  # Небольшая пауза
            
            # Загружаем видео
            clip = VideoFileClip(temp_video_path)
            
            # Применяем параметры обработки
            width = kwargs.get('width', 480)
            fps = kwargs.get('fps', 15)
            start_time = kwargs.get('start_time', 0)
            end_time = kwargs.get('end_time', None)
            keep_original_size = kwargs.get('keep_original_size', False)
            speed = kwargs.get('speed', 1.0) or 1.0
            grayscale = kwargs.get('grayscale', False)
            reverse = kwargs.get('reverse', False)
            boomerang = kwargs.get('boomerang', False)
            # high_quality и dither не влияют на MoviePy напрямую
            
            from moviepy import vfx as mvfx
            
            # Обрезка по времени
            if end_time:
                clip = clip.subclip(start_time, end_time)
            elif start_time > 0:
                clip = clip.subclip(start_time)
            
            # Скорость
            if speed and float(speed) != 1.0:
                try:
                    clip = clip.fx(mvfx.speedx, factor=float(speed))
                except Exception:
                    pass
            
            # Эффекты: бумеранг/реверс/монохром
            if boomerang:
                rev = clip.fx(mvfx.time_mirror)
                from moviepy.editor import concatenate_videoclips
                clip = concatenate_videoclips([clip, rev])
            elif reverse:
                clip = clip.fx(mvfx.time_mirror)
            
            if grayscale:
                try:
                    clip = clip.fx(mvfx.blackwhite)
                except Exception:
                    pass
            
            # Изменение размера (если не сохраняем оригинальные размеры)
            if not keep_original_size and width:
                try:
                    # Новая версия MoviePy
                    clip = clip.resized(width=width)
                except AttributeError:
                    # Старая версия MoviePy  
                    clip = clip.resize(width=width)
            
            # Конвертация в GIF (базовые параметры)
            clip.write_gif(output_path, fps=fps)
            
            logger.info(f"Видео успешно конвертировано в GIF: {output_path}")
            return True
                    
        except ImportError:
            logger.warning("MoviePy не установлен, переключаемся на FFmpeg")
            return self._convert_with_ffmpeg(video_file, output_path, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка при конвертации с MoviePy: {str(e)}")
            return False
        finally:
            # Освобождение ресурсов
            if clip is not None:
                try:
                    clip.close()
                except:
                    pass
            
            # Удаляем временный файл с несколькими попытками
            if temp_video_path and os.path.exists(temp_video_path):
                import time
                for attempt in range(3):
                    try:
                        os.unlink(temp_video_path)
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(0.5)
                        else:
                            logger.warning(f"Не удалось удалить временный файл: {temp_video_path}")
    
    def _convert_with_ffmpeg(self, video_file, output_path, **kwargs):
        """
        Конвертация с использованием FFmpeg.
        """
        try:
            ffmpeg_path = getattr(settings, 'FFMPEG_BINARY', 'ffmpeg')
            
            # Проверяем доступность FFmpeg
            if not self._check_ffmpeg(ffmpeg_path):
                logger.error("FFmpeg не найден или недоступен")
                return False
            
            # Сохраняем временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                for chunk in video_file.chunks():
                    temp_file.write(chunk)
                temp_video_path = temp_file.name
            
            try:
                # Подготовка параметров FFmpeg
                width = kwargs.get('width', 480)
                fps = kwargs.get('fps', 15)
                start_time = kwargs.get('start_time', 0)
                end_time = kwargs.get('end_time', None)
                keep_original_size = kwargs.get('keep_original_size', False)
                speed = float(kwargs.get('speed', 1.0) or 1.0)
                grayscale = kwargs.get('grayscale', False)
                reverse = kwargs.get('reverse', False)
                boomerang = kwargs.get('boomerang', False)
                high_quality = kwargs.get('high_quality', False)
                dither = (kwargs.get('dither') or 'bayer')
                
                # Если нужны сложные эффекты, передадим в MoviePy
                if reverse or boomerang:
                    logger.info("Сложные эффекты (reverse/boomerang) - используем MoviePy")
                    return self._convert_with_moviepy(video_file, output_path, **kwargs)
                
                # Строим команду FFmpeg
                cmd = [ffmpeg_path, '-i', temp_video_path]
                
                # Добавляем параметры времени
                if start_time > 0:
                    cmd.extend(['-ss', str(start_time)])
                
                if end_time:
                    duration = end_time - start_time
                    cmd.extend(['-t', str(duration)])
                
                # Базовый фильтр: изменение скорости -> fps -> scale -> grayscale
                filter_parts = []
                if speed and speed != 1.0:
                    # setpts=PTS/Speed
                    filter_parts.append(f"setpts=PTS/{speed}")
                
                filter_parts.append(f"fps={fps}")
                if not keep_original_size:
                    filter_parts.append(f"scale={width}:-1:flags=fast_bilinear")
                if grayscale:
                    filter_parts.append("format=gray")
                
                base_filter = ",".join(filter_parts) if filter_parts else "null"
                
                if high_quality:
                    # Двухпроходная палитра
                    palette = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                    try:
                        # Шаг 1: palettegen
                        pg_cmd = [ffmpeg_path, '-i', temp_video_path]
                        if start_time > 0:
                            pg_cmd.extend(['-ss', str(start_time)])
                        if end_time:
                            duration = end_time - start_time
                            pg_cmd.extend(['-t', str(duration)])
                        pg_cmd.extend(['-vf', f"{base_filter},palettegen=max_colors=256", '-y', palette])
                        pg_res = subprocess.run(pg_cmd, capture_output=True, text=True, timeout=300)
                        if pg_res.returncode != 0:
                            logger.error(f"palettegen error: {pg_res.stderr}")
                            return False
                        
                        # Шаг 2: paletteuse с дизерингом
                        pu_filter = f"{base_filter}[x];[x][1:v]paletteuse=dither={dither}"
                        cmd = [ffmpeg_path, '-i', temp_video_path, '-i', palette, '-lavfi', pu_filter, '-y', output_path]
                        pu_res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                        if pu_res.returncode == 0:
                            logger.info(f"Видео успешно конвертировано в GIF (paletteuse): {output_path}")
                            return True
                        else:
                            logger.error(f"paletteuse error: {pu_res.stderr}")
                            return False
                    finally:
                        try:
                            os.unlink(palette)
                        except Exception:
                            pass
                else:
                    # Простой однопроходный фильтр
                    video_filter = base_filter
                    cmd.extend(['-vf', video_filter, '-y', output_path])
                    
                    # Выполняем команду
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 минут таймаут
                    )
                
                if result.returncode == 0:
                    logger.info(f"Видео успешно конвертировано в GIF: {output_path}")
                    return True
                else:
                    logger.error(f"Ошибка FFmpeg: {result.stderr}")
                    return False
                    
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_video_path):
                    os.unlink(temp_video_path)
                    
        except subprocess.TimeoutExpired:
            logger.error("Таймаут при конвертации видео")
            return False
        except Exception as e:
            logger.error(f"Ошибка при конвертации с FFmpeg: {str(e)}")
            return False
    
    def convert_to_gif(self, input_path, output_path, width=None, fps=15, start_time=0, end_time=None, grayscale=False, reverse=False, boomerang=False):
        """
        Метод-обертка для совместимости с существующим кодом.
        Конвертирует видео в GIF с указанными параметрами.
        
        Args:
            input_path: Путь к входному видеофайлу
            output_path: Путь для сохранения GIF
            width: Ширина выходного GIF
            fps: Частота кадров
            start_time: Время начала (секунды)
            end_time: Время окончания (секунды)
            grayscale: Черно-белый режим
            reverse: Реверс видео
            boomerang: Эффект бумеранга
            
        Returns:
            bool: True если конвертация прошла успешно
        """
        try:
            # Создаем объект файла из пути
            class FileWrapper:
                def __init__(self, file_path):
                    self.file_path = file_path
                    self.name = os.path.basename(file_path)
                    
                def chunks(self, chunk_size=8192):
                    with open(self.file_path, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk
            
            file_wrapper = FileWrapper(input_path)
            
            # Вызываем основной метод конвертации
            return self.convert_video_to_gif(
                video_file=file_wrapper,
                output_path=output_path,
                width=width,
                fps=fps,
                start_time=start_time,
                end_time=end_time,
                grayscale=grayscale,
                reverse=reverse,
                boomerang=boomerang
            )
        except Exception as e:
            logger.error(f"Ошибка в convert_to_gif: {str(e)}")
            return False
    
    def _check_ffmpeg(self, ffmpeg_path):
        """
        Проверяет доступность FFmpeg.
        """
        try:
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
    
    def get_video_info(self, video_file):
        """
        Получает информацию о видео файле.
        Пробует FFmpeg, если не работает - использует MoviePy.
        
        Args:
            video_file: Загруженный файл видео
        
        Returns:
            dict: Словарь с информацией о видео
        """
        # Сначала пробуем FFmpeg
        try:
            ffmpeg_path = getattr(settings, 'FFMPEG_BINARY', 'ffmpeg')
            
            # Сохраняем временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                for chunk in video_file.chunks():
                    temp_file.write(chunk)
                temp_video_path = temp_file.name
            
            try:
                # Используем ffprobe для получения информации
                ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
                
                cmd = [
                    ffprobe_path,
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    '-show_streams',
                    temp_video_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    import json
                    info = json.loads(result.stdout)
                    
                    # Извлекаем основную информацию
                    video_stream = None
                    for stream in info.get('streams', []):
                        if stream.get('codec_type') == 'video':
                            video_stream = stream
                            break
                    
                    if video_stream:
                        return {
                            'duration': float(info.get('format', {}).get('duration', 0)),
                            'width': video_stream.get('width', 0),
                            'height': video_stream.get('height', 0),
                            'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                            'codec': video_stream.get('codec_name', 'unknown'),
                            'bitrate': int(info.get('format', {}).get('bit_rate', 0))
                        }
                
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_video_path):
                    os.unlink(temp_video_path)
                    
        except Exception as e:
            logger.warning(f"FFmpeg недоступен, пробуем MoviePy: {str(e)}")
        
        # Fallback на MoviePy
        try:
            try:
                from moviepy.editor import VideoFileClip
            except ImportError:
                # Fallback for newer MoviePy versions
                from moviepy import VideoFileClip
            
            # Сохраняем временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                for chunk in video_file.chunks():
                    temp_file.write(chunk)
                temp_video_path = temp_file.name
            
            try:
                clip = VideoFileClip(temp_video_path)
                info = {
                    'duration': clip.duration,
                    'width': clip.w,
                    'height': clip.h,
                    'fps': clip.fps,
                    'codec': 'unknown',
                    'bitrate': 0
                }
                clip.close()
                return info
                
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_video_path):
                    os.unlink(temp_video_path)
                    
        except Exception as e:
            logger.error(f"Ошибка при получении информации о видео: {str(e)}")
            return {}


def save_uploaded_video(video_file):
    """
    Сохраняет загруженное видео во временную директорию.
    
    Args:
        video_file: Загруженный файл
    
    Returns:
        str: Путь к сохраненному файлу
    """
    try:
        # Создаем папку для загрузок если её нет
        upload_dir = Path(settings.MEDIA_ROOT) / 'uploads' / 'videos'
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерируем уникальное имя файла
        import uuid
        file_extension = video_file.name.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Сохраняем файл
        with open(file_path, 'wb') as f:
            for chunk in video_file.chunks():
                f.write(chunk)
        
        return str(file_path)
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла: {str(e)}")
        return None


def save_converted_gif(gif_path, original_filename):
    """
    Сохраняет конвертированный GIF в медиа папку.
    
    Args:
        gif_path: Путь к временному GIF файлу
        original_filename: Оригинальное имя видео файла
    
    Returns:
        str: URL для скачивания GIF
    """
    try:
        # Создаем папку для GIF если её нет
        gif_dir = Path(settings.MEDIA_ROOT) / 'gifs'
        gif_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерируем безопасное имя для GIF (без пробелов и спецсимволов)
        import uuid
        import re
        base_name = original_filename.rsplit('.', 1)[0]
        # Очищаем имя от нежелательных символов
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)[:20]  # Ограничиваем длину
        gif_filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.gif"
        final_gif_path = gif_dir / gif_filename
        
        # Копируем файл
        import shutil
        logger.info(f"Перемещаем GIF с {gif_path} на {final_gif_path}")
        
        if os.path.exists(gif_path):
            shutil.move(gif_path, final_gif_path)
            logger.info(f"GIF успешно перемещен: {final_gif_path}")
            logger.info(f"Размер файла: {os.path.getsize(final_gif_path)} байт")
        else:
            logger.error(f"Временный GIF файл не найден: {gif_path}")
            return None
        
        # Возвращаем URL
        gif_url = f"{settings.MEDIA_URL}gifs/{gif_filename}"
        logger.info(f"Генерируем URL для GIF: {gif_url}")
        return gif_url
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении GIF: {str(e)}")
        return None


def cleanup_temp_files(file_paths):
    """
    Очищает временные файлы.
    
    Args:
        file_paths: Список путей к файлам для удаления
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл {file_path}: {str(e)}")


class PhotoToGifConverter:
    """
    Класс для создания GIF анимации из фотографий.
    """
    
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    def create_gif_from_photos(self, photo_files, output_path, **kwargs):
        """
        Создает GIF анимацию из списка фотографий.
        
        Args:
            photo_files: Список загруженных фото файлов
            output_path: Путь для сохранения GIF
            **kwargs: Дополнительные параметры
                - duration: длительность показа каждого кадра (мс)
                - loop: количество повторений (0 - бесконечно)
                - quality: качество оптимизации (1-100)
                - resize: изменить размер (width, height)
                - transition: тип перехода между кадрами
                - reverse: добавить обратную последовательность
        
        Returns:
            bool: True если создание GIF прошло успешно
        """
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            import io
            
            if not photo_files:
                logger.error("Не предоставлено ни одного фото")
                return False
            
            # Параметры по умолчанию
            duration = kwargs.get('duration', 500)  # мс
            loop = kwargs.get('loop', 0)  # 0 = бесконечно
            quality = kwargs.get('quality', 85)
            resize = kwargs.get('resize', None)  # (width, height) или None
            transition = kwargs.get('transition', 'none')  # none, fade, slide
            reverse = kwargs.get('reverse', False)
            optimize = kwargs.get('optimize', True)
            
            logger.info(f"Создаем GIF из {len(photo_files)} фото с параметрами: duration={duration}, loop={loop}, quality={quality}")
            
            # Загружаем и обрабатываем изображения
            frames = []
            max_width, max_height = 0, 0
            
            for i, photo_file in enumerate(photo_files):
                try:
                    # Проверяем формат файла
                    if not self._is_supported_format(photo_file.name):
                        logger.warning(f"Неподдерживаемый формат файла: {photo_file.name}")
                        continue
                    
                    # Открываем изображение
                    image_data = photo_file.read()
                    photo_file.seek(0)  # Сбрасываем указатель файла
                    
                    with Image.open(io.BytesIO(image_data)) as img:
                        # Конвертируем в RGB если нужно
                        if img.mode not in ['RGB', 'RGBA']:
                            img = img.convert('RGB')
                        
                        # Поворот по EXIF если есть
                        img = self._fix_image_orientation(img)
                        
                        # Изменение размера
                        if resize:
                            img = img.resize(resize, Image.Resampling.LANCZOS)
                        else:
                            # Запоминаем максимальные размеры для нормализации
                            max_width = max(max_width, img.width)
                            max_height = max(max_height, img.height)
                        
                        frames.append(img.copy())
                        
                except Exception as e:
                    logger.error(f"Ошибка обработки фото {i+1}: {str(e)}")
                    continue
            
            if not frames:
                logger.error("Не удалось загрузить ни одного изображения")
                return False
            
            # Нормализация размеров если не задан resize
            if not resize and len(frames) > 1:
                frames = self._normalize_frame_sizes(frames, max_width, max_height)
            
            # Добавляем эффекты перехода
            if transition != 'none':
                frames = self._add_transition_effects(frames, transition, duration)
            
            # Добавляем обратную последовательность для bounce эффекта
            if reverse:
                # Добавляем кадры в обратном порядке (кроме первого и последнего)
                reverse_frames = frames[-2:0:-1]
                frames.extend(reverse_frames)
            
            # Оптимизация палитры
            if optimize and len(frames) > 1:
                frames = self._optimize_palette(frames)
            
            # Создаем и сохраняем GIF
            if frames:
                first_frame = frames[0]
                
                # Настройки сохранения
                save_kwargs = {
                    'save_all': True,
                    'append_images': frames[1:] if len(frames) > 1 else [],
                    'duration': duration,
                    'loop': loop,
                    'optimize': optimize,
                }
                
                # Дополнительные настройки качества
                if quality < 95:
                    save_kwargs['quality'] = quality
                
                first_frame.save(output_path, 'GIF', **save_kwargs)
                
                logger.info(f"GIF успешно создан: {output_path}")
                logger.info(f"Количество кадров: {len(frames)}")
                logger.info(f"Размер файла: {os.path.getsize(output_path)} байт")
                
                return True
            else:
                logger.error("Нет кадров для создания GIF")
                return False
                
        except ImportError:
            logger.error("Pillow не установлен для создания GIF из фото")
            return False
        except Exception as e:
            logger.error(f"Ошибка при создании GIF из фото: {str(e)}")
            return False
    
    def _is_supported_format(self, filename):
        """
        Проверяет поддерживается ли формат файла.
        """
        if not filename:
            return False
        extension = os.path.splitext(filename.lower())[1]
        return extension in self.supported_formats
    
    def _fix_image_orientation(self, img):
        """
        Исправляет ориентацию изображения по EXIF данным.
        """
        try:
            from PIL.ExifTags import ORIENTATION
            
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif:
                    orientation = exif.get(ORIENTATION)
                    if orientation == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation == 8:
                        img = img.rotate(90, expand=True)
        except:
            pass
        return img
    
    def _normalize_frame_sizes(self, frames, target_width, target_height):
        """
        Приводит все кадры к одному размеру.
        """
        normalized_frames = []
        for frame in frames:
            if frame.size != (target_width, target_height):
                # Изменяем размер с сохранением пропорций
                frame.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                
                # Создаем новое изображение с нужным размером и вставляем по центру
                new_frame = Image.new('RGB', (target_width, target_height), (255, 255, 255))
                x = (target_width - frame.width) // 2
                y = (target_height - frame.height) // 2
                new_frame.paste(frame, (x, y))
                normalized_frames.append(new_frame)
            else:
                normalized_frames.append(frame)
        return normalized_frames
    
    def _add_transition_effects(self, frames, transition, duration):
        """
        Добавляет эффекты перехода между кадрами.
        """
        if transition == 'fade' and len(frames) > 1:
            return self._add_fade_transition(frames, duration)
        elif transition == 'slide' and len(frames) > 1:
            return self._add_slide_transition(frames, duration)
        return frames
    
    def _add_fade_transition(self, frames, duration):
        """
        Добавляет плавный переход между кадрами.
        """
        from PIL import Image, ImageEnhance
        
        enhanced_frames = []
        fade_steps = 5  # Количество промежуточных кадров
        
        for i in range(len(frames)):
            enhanced_frames.append(frames[i])
            
            # Добавляем fade переходы между кадрами
            if i < len(frames) - 1:
                current_frame = frames[i]
                next_frame = frames[i + 1]
                
                for step in range(1, fade_steps):
                    alpha = step / fade_steps
                    
                    # Создаем промежуточный кадр
                    blended = Image.blend(current_frame.convert('RGB'), next_frame.convert('RGB'), alpha)
                    enhanced_frames.append(blended)
        
        return enhanced_frames
    
    def _add_slide_transition(self, frames, duration):
        """
        Добавляет скользящий переход между кадрами.
        """
        enhanced_frames = []
        slide_steps = 3  # Количество промежуточных кадров
        
        for i in range(len(frames)):
            enhanced_frames.append(frames[i])
            
            # Добавляем slide переходы между кадрами
            if i < len(frames) - 1:
                current_frame = frames[i]
                next_frame = frames[i + 1]
                width, height = current_frame.size
                
                for step in range(1, slide_steps):
                    offset = int(width * step / slide_steps)
                    
                    # Создаем промежуточный кадр со скольжением
                    slide_frame = Image.new('RGB', (width, height), (255, 255, 255))
                    slide_frame.paste(current_frame, (-offset, 0))
                    slide_frame.paste(next_frame, (width - offset, 0))
                    enhanced_frames.append(slide_frame)
        
        return enhanced_frames
    
    def _optimize_palette(self, frames):
        """
        Оптимизирует цветовую палитру для уменьшения размера файла.
        """
        try:
            # Конвертируем все кадры в режим P (с палитрой) для лучшего сжатия
            optimized_frames = []
            
            # Создаем общую палитру из всех кадров
            if frames:
                # Берем первый кадр как основу для палитры
                first_frame = frames[0]
                if first_frame.mode != 'P':
                    first_frame = first_frame.convert('P', palette=Image.ADAPTIVE, colors=256)
                
                optimized_frames.append(first_frame)
                
                # Применяем ту же палитру к остальным кадрам
                for frame in frames[1:]:
                    if frame.mode != 'P':
                        # Используем палитру первого кадра
                        frame = frame.quantize(palette=first_frame)
                    optimized_frames.append(frame)
                
            return optimized_frames if optimized_frames else frames
        except:
            # Если оптимизация не удалась, возвращаем оригинальные кадры
            return frames


def save_uploaded_photos(photo_files):
    """
    Сохраняет загруженные фото во временную директорию.
    
    Args:
        photo_files: Список загруженных фото файлов
    
    Returns:
        list: Список путей к сохраненным файлам
    """
    try:
        # Создаем папку для загрузок если её нет
        upload_dir = Path(settings.MEDIA_ROOT) / 'uploads' / 'photos'
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        
        for i, photo_file in enumerate(photo_files):
            try:
                # Генерируем уникальное имя файла
                import uuid
                file_extension = photo_file.name.split('.')[-1] if '.' in photo_file.name else 'jpg'
                unique_filename = f"{uuid.uuid4()}_{i}.{file_extension}"
                file_path = upload_dir / unique_filename
                
                # Сохраняем файл
                with open(file_path, 'wb') as f:
                    for chunk in photo_file.chunks():
                        f.write(chunk)
                
                saved_paths.append(str(file_path))
                
            except Exception as e:
                logger.error(f"Ошибка при сохранении фото {i+1}: {str(e)}")
                continue
        
        return saved_paths
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении фото: {str(e)}")
        return []
