"""
Video conversion service with hardened FFmpeg backend.
Supports synchronous and asynchronous (Celery) task processing.
"""

import os
import uuid
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from django.conf import settings
from django.utils import timezone
from .models import ConversionTask
from .utils import VideoConverter

logger = logging.getLogger(__name__)


class VideoConversionService:
    """
    Service for handling video to GIF conversions with hardened FFmpeg backend.
    """
    
    def __init__(self):
        self.ffmpeg_path = getattr(settings, 'FFMPEG_BINARY', 'ffmpeg')
        self.timeout = getattr(settings, 'VIDEO_PROCESSING_TIMEOUT', 300)
        self.output_dir = Path(settings.MEDIA_ROOT) / 'converted'
        self.output_dir.mkdir(exist_ok=True)
        
    def convert_video_to_gif(
        self,
        task_id: int,
        input_path: str,
        video_file=None,
        width: Optional[int] = None,
        fps: int = 15,
        start_time: int = 0,
        end_time: Optional[int] = None,
        keep_original_size: bool = False,
        speed: float = 1.0,
        grayscale: bool = False,
        reverse: bool = False,
        boomerang: bool = False,
        high_quality: bool = False,
        dither: str = 'bayer',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convert video to GIF using FFmpeg with advanced options.
        
        Args:
            task_id: ConversionTask ID for progress tracking
            input_path: Path to input video file
            video_file: Django uploaded file (unused, kept for compatibility)
            width: Output width in pixels (ignored if keep_original_size=True)
            fps: Frames per second for output GIF
            start_time: Start time in seconds
            end_time: End time in seconds (None for entire video)
            keep_original_size: Whether to maintain original video dimensions
            speed: Playback speed multiplier
            grayscale: Convert to grayscale
            reverse: Reverse playback
            boomerang: Boomerang effect (forward then backward)
            high_quality: Use high quality palette generation
            dither: Dithering algorithm ('bayer', 'sierra2_4a', 'floyd_steinberg', 'none')
            **kwargs: Additional options
            
        Returns:
            Dict with success status, output_path, and error_message
        """
        temp_files = []
        
        try:
            # Get task from database
            task = ConversionTask.objects.get(id=task_id)
            task.start()
            
            # Validate input file
            if not os.path.exists(input_path):
                return {
                    'success': False,
                    'error_message': 'Входной файл не найден'
                }
            
            # Check FFmpeg availability
            if not self._check_ffmpeg():
                return {
                    'success': False,
                    'error_message': 'FFmpeg не найден или недоступен'
                }
            
            # Validate video file and get metadata
            video_info = self._get_video_info(input_path)
            if not video_info['valid']:
                task.fail('Неподдерживаемый формат видео или повреждённый файл')
                return {
                    'success': False,
                    'error_message': 'Неподдерживаемый формат видео или повреждённый файл'
                }
            
            # Validate time range
            duration = video_info.get('duration', 0)
            if end_time and end_time > duration:
                task.fail('Время окончания превышает длительность видео')
                return {
                    'success': False,
                    'error_message': f'Время окончания превышает длительность видео ({duration:.1f} сек)'
                }
            
            if start_time >= duration:
                task.fail('Время начала превышает длительность видео')
                return {
                    'success': False,
                    'error_message': f'Время начала превышает длительность видео ({duration:.1f} сек)'
                }
            
            # Update progress
            self._update_task_progress(task_id, 20, "Начинаем конвертацию видео")
            
            # Generate output filename
            output_filename = f"{uuid.uuid4()}.gif"
            output_path = self.output_dir / output_filename
            
            # Perform conversion based on complexity
            if reverse or boomerang:
                # Complex effects require multiple passes or special handling
                success = self._convert_with_complex_effects(
                    input_path, str(output_path), task_id,
                    width=width, fps=fps, start_time=start_time, end_time=end_time,
                    keep_original_size=keep_original_size, speed=speed,
                    grayscale=grayscale, reverse=reverse, boomerang=boomerang,
                    high_quality=high_quality, dither=dither
                )
            else:
                # Standard conversion with FFmpeg
                success = self._convert_with_ffmpeg(
                    input_path, str(output_path), task_id,
                    width=width, fps=fps, start_time=start_time, end_time=end_time,
                    keep_original_size=keep_original_size, speed=speed,
                    grayscale=grayscale, high_quality=high_quality, dither=dither
                )
            
            if success and os.path.exists(output_path):
                # Update task completion
                task.set_metadata(
                    output_path=str(output_path),
                    output_format='gif',
                    output_size=os.path.getsize(output_path)
                )
                task.complete()
                
                self._update_task_progress(task_id, 100, "Конвертация завершена")
                
                return {
                    'success': True,
                    'output_path': str(output_path),
                    'output_filename': output_filename,
                    'file_size': os.path.getsize(output_path)
                }
            else:
                task.fail('Ошибка при создании GIF файла')
                return {
                    'success': False,
                    'error_message': 'Ошибка при создании GIF файла'
                }
                
        except ConversionTask.DoesNotExist:
            return {
                'success': False,
                'error_message': 'Задача конвертации не найдена'
            }
        except Exception as e:
            logger.error(f"Conversion error for task {task_id}: {e}")
            try:
                task = ConversionTask.objects.get(id=task_id)
                task.fail(str(e))
            except:
                pass
            
            return {
                'success': False,
                'error_message': f'Внутренняя ошибка: {str(e)}'
            }
        finally:
            # Cleanup temporary files
            self._cleanup_temp_files(temp_files)
    
    def _convert_with_ffmpeg(
        self,
        input_path: str,
        output_path: str,
        task_id: int,
        width: Optional[int],
        fps: int,
        start_time: int,
        end_time: Optional[int],
        keep_original_size: bool,
        speed: float,
        grayscale: bool,
        high_quality: bool,
        dither: str
    ) -> bool:
        """
        Standard FFmpeg conversion without complex effects.
        """
        try:
            self._update_task_progress(task_id, 30, "Подготовка FFmpeg команды")
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_path]
            
            # Input file
            cmd.extend(['-i', input_path])
            
            # Time parameters
            if start_time > 0:
                cmd.extend(['-ss', str(start_time)])
            
            if end_time:
                duration = end_time - start_time
                cmd.extend(['-t', str(duration)])
            
            # Build video filter chain
            filters = []
            
            # Speed adjustment
            if speed != 1.0:
                filters.append(f"setpts=PTS/{speed}")
            
            # Frame rate
            filters.append(f"fps={fps}")
            
            # Scaling (unless keeping original size)
            if not keep_original_size and width:
                filters.append(f"scale={width}:-1:flags=lanczos")
            
            # Color format
            if grayscale:
                filters.append("format=gray")
            else:
                filters.append("format=rgb24")
            
            if high_quality:
                # Two-pass palette generation for high quality
                return self._convert_with_palette(
                    input_path, output_path, task_id, filters, dither,
                    start_time, end_time
                )
            else:
                # Single-pass conversion
                filter_chain = ",".join(filters)
                cmd.extend(['-vf', filter_chain])
                
                # GIF-specific options
                cmd.extend(['-gifflags', '-offsetting'])
                cmd.extend(['-y', output_path])  # Overwrite output
                
                self._update_task_progress(task_id, 50, "Выполняем конвертацию")
                
                # Run FFmpeg
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                if result.returncode == 0:
                    self._update_task_progress(task_id, 90, "Конвертация завершена")
                    logger.info(f"FFmpeg conversion successful: {output_path}")
                    return True
                else:
                    logger.error(f"FFmpeg error: {result.stderr}")
                    return False
                    
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout for task {task_id}")
            return False
        except Exception as e:
            logger.error(f"FFmpeg conversion error: {e}")
            return False
    
    def _convert_with_palette(
        self,
        input_path: str,
        output_path: str,
        task_id: int,
        base_filters: list,
        dither: str,
        start_time: int,
        end_time: Optional[int]
    ) -> bool:
        """
        Two-pass conversion with palette generation for high quality.
        """
        try:
            palette_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            
            self._update_task_progress(task_id, 40, "Генерация цветовой палитры")
            
            # Step 1: Generate palette
            palette_cmd = [self.ffmpeg_path, '-i', input_path]
            
            if start_time > 0:
                palette_cmd.extend(['-ss', str(start_time)])
            
            if end_time:
                duration = end_time - start_time
                palette_cmd.extend(['-t', str(duration)])
            
            filter_chain = ",".join(base_filters + ["palettegen=max_colors=256"])
            palette_cmd.extend(['-vf', filter_chain, '-y', palette_path])
            
            palette_result = subprocess.run(
                palette_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout // 2,
                encoding='utf-8',
                errors='ignore'
            )
            
            if palette_result.returncode != 0:
                logger.error(f"Palette generation failed: {palette_result.stderr}")
                return False
            
            self._update_task_progress(task_id, 60, "Применение палитры")
            
            # Step 2: Use palette for final conversion
            final_cmd = [self.ffmpeg_path, '-i', input_path, '-i', palette_path]
            
            if start_time > 0:
                final_cmd.extend(['-ss', str(start_time)])
            
            if end_time:
                duration = end_time - start_time
                final_cmd.extend(['-t', str(duration)])
            
            # Complex filter with palette use
            base_chain = ",".join(base_filters)
            complex_filter = f"{base_chain}[x];[x][1:v]paletteuse=dither={dither}"
            final_cmd.extend(['-lavfi', complex_filter])
            final_cmd.extend(['-y', output_path])
            
            final_result = subprocess.run(
                final_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                errors='ignore'
            )
            
            # Cleanup palette file
            try:
                os.unlink(palette_path)
            except:
                pass
            
            if final_result.returncode == 0:
                self._update_task_progress(task_id, 90, "Высококачественная конвертация завершена")
                logger.info(f"High-quality FFmpeg conversion successful: {output_path}")
                return True
            else:
                logger.error(f"Final FFmpeg error: {final_result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg palette timeout for task {task_id}")
            return False
        except Exception as e:
            logger.error(f"Palette conversion error: {e}")
            return False
    
    def _convert_with_complex_effects(
        self,
        input_path: str,
        output_path: str,
        task_id: int,
        **kwargs
    ) -> bool:
        """
        Handle complex effects (reverse, boomerang) using multiple passes or video processing libraries.
        """
        try:
            self._update_task_progress(task_id, 35, "Обработка сложных эффектов")
            
            # For complex effects, use the existing VideoConverter with MoviePy
            video_converter = VideoConverter(use_moviepy=True)
            
            # Create a temporary file object-like interface
            class TempVideoFile:
                def __init__(self, file_path):
                    self.path = file_path
                    self.name = os.path.basename(file_path)
                
                def chunks(self):
                    # Read file in chunks
                    with open(self.path, 'rb') as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            yield chunk
            
            temp_video_file = TempVideoFile(input_path)
            
            success = video_converter.convert_video_to_gif(
                temp_video_file, output_path, **kwargs
            )
            
            if success:
                self._update_task_progress(task_id, 85, "Сложные эффекты применены")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Complex effects conversion error: {e}")
            return False
    
    def _get_video_info(self, input_path: str) -> Dict[str, Any]:
        """
        Get video metadata using FFprobe.
        """
        try:
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
            
            cmd = [
                ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                input_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # Find video stream
                video_stream = None
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                        break
                
                if video_stream:
                    duration = float(data.get('format', {}).get('duration', 0))
                    
                    return {
                        'valid': True,
                        'duration': duration,
                        'width': int(video_stream.get('width', 0)),
                        'height': int(video_stream.get('height', 0)),
                        'codec': video_stream.get('codec_name', 'unknown'),
                        'fps': eval(video_stream.get('r_frame_rate', '0/1'))
                    }
            
            return {'valid': False}
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {'valid': False}
    
    def _check_ffmpeg(self) -> bool:
        """
        Check if FFmpeg is available and working.
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _update_task_progress(self, task_id: int, progress: int, message: str = ""):
        """
        Update task progress in database.
        """
        try:
            task = ConversionTask.objects.get(id=task_id)
            task.update_progress(progress)
            
            if message:
                metadata = task.task_metadata or {}
                metadata['last_message'] = message
                metadata['last_updated'] = timezone.now().isoformat()
                task.task_metadata = metadata
                task.save(update_fields=['task_metadata'])
                
            logger.info(f'Task {task_id}: {progress}% - {message}')
            
        except ConversionTask.DoesNotExist:
            logger.warning(f'Task {task_id} not found in database')
        except Exception as e:
            logger.error(f'Error updating task progress {task_id}: {e}')
    
    def _cleanup_temp_files(self, temp_files: list):
        """
        Clean up temporary files.
        """
        for file_path in temp_files:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f'Cleaned up temp file: {file_path}')
            except Exception as e:
                logger.warning(f'Failed to clean up temp file {file_path}: {e}')
