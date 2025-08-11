"""
Адаптер для конвертации аудио файлов.
Использует pydub и ffmpeg для обработки различных аудио форматов.
"""

from typing import Dict, List, Any, Union
import logging
from pathlib import Path
from django.conf import settings
from .base import BaseEngine, ConversionResult

logger = logging.getLogger(__name__)


class AudioEngine(BaseEngine):
    """
    Engine для конвертации аудио файлов.
    Использует pydub и ffmpeg для обработки различных аудио форматов.
    """
    
    def __init__(self):
        super().__init__()
        self.engine_type = 'audio'
    
    def check_dependencies(self) -> Dict[str, bool]:
        """
        Проверяет доступность зависимостей для работы с аудио.
        """
        deps = {}
        
        # Проверка pydub
        try:
            import pydub
            deps['pydub'] = True
        except ImportError:
            deps['pydub'] = False
        
        # Проверка ffmpeg через pydub
        try:
            from pydub.utils import which
            deps['ffmpeg'] = which('ffmpeg') is not None
        except:
            deps['ffmpeg'] = False
        
        # Проверка simpleaudio для воспроизведения (опционально)
        try:
            import simpleaudio
            deps['simpleaudio'] = True
        except ImportError:
            deps['simpleaudio'] = False
            
        return deps
    
    def is_available(self) -> bool:
        """
        Проверяет, доступен ли движок для использования.
        """
        deps = self.check_dependencies()
        return deps.get('pydub', False) and deps.get('ffmpeg', False)
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """
        Возвращает поддерживаемые форматы.
        """
        return {
            'input': ['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'wma', 'opus', 'amr'],
            'output': ['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'opus']
        }
    
    def validate_input(self, input_file: Union[str, Path, Any]) -> bool:
        """
        Проверяет валидность входного аудио файла.
        
        Args:
            input_file: Входной файл для проверки (путь к файлу или Django UploadedFile)
            
        Returns:
            bool: True если файл валиден, False иначе
        """
        try:
            # Получаем поддерживаемые форматы
            supported_formats = self.get_supported_formats()['input']
            
            # Проверяем тип входного файла
            if hasattr(input_file, 'size') and hasattr(input_file, 'name'):
                # Django UploadedFile
                file_name = input_file.name
                file_size = input_file.size
                
                # Проверяем, что файл не пустой
                if file_size == 0:
                    logger.warning("Файл пустой")
                    return False
                    
            else:
                # Путь к файлу
                file_path = Path(input_file)
                
                # Проверяем существование файла
                if not file_path.exists():
                    logger.warning(f"Файл не существует: {file_path}")
                    return False
                
                # Проверяем, что это файл, а не директория
                if not file_path.is_file():
                    logger.warning(f"Путь не указывает на файл: {file_path}")
                    return False
                
                file_name = file_path.name
                file_size = file_path.stat().st_size
                
                # Проверяем, что файл не пустой
                if file_size == 0:
                    logger.warning(f"Файл пустой: {file_path}")
                    return False
            
            # Проверяем расширение файла
            if '.' not in file_name:
                logger.warning(f"Файл без расширения: {file_name}")
                return False
            
            file_extension = file_name.split('.')[-1].lower()
            if file_extension not in supported_formats:
                logger.warning(f"Неподдерживаемое расширение: {file_extension}. Поддерживаемые: {supported_formats}")
                return False
            
            # Проверяем размер файла
            max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 500 * 1024 * 1024)  # 500MB по умолчанию
            if file_size > max_size:
                logger.warning(f"Файл слишком большой: {file_size} байт, максимум: {max_size} байт")
                return False
            
            logger.debug(f"Валидация файла прошла успешно: {file_name}, размер: {file_size} байт")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при валидации входного файла: {e}")
            return False
    
    def get_audio_info(self, input_file) -> Dict:
        """
        Получает информацию об аудио файле.
        """
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(input_file)
            
            return {
                'duration': len(audio) / 1000.0,  # в секундах
                'channels': audio.channels,
                'frame_rate': audio.frame_rate,
                'sample_width': audio.sample_width,
                'max_possible_amplitude': audio.max_possible_amplitude,
                'rms': audio.rms,
                'dBFS': audio.dBFS
            }
        except Exception as e:
            logger.error(f"Error getting audio info: {e}")
            return {'error': str(e)}
    
    def convert(
        self, 
        input_file, 
        output_path: str, 
        output_format: str = None,
        **kwargs
    ) -> ConversionResult:
        """
        Конвертирует аудио файл.
        
        Поддерживаемые параметры:
        - output_format: выходной формат (mp3, wav, flac, etc.)
        - bitrate: битрейт для MP3 (например, '192k', '320k')
        - sample_rate: частота дискретизации (22050, 44100, 48000, etc.)
        - channels: количество каналов (1 = mono, 2 = stereo)
        - start_time: время начала в секундах
        - end_time: время окончания в секундах
        - volume_change: изменение громкости в дБ (+/-)
        - fade_in: время плавного появления в секундах
        - fade_out: время плавного исчезновения в секундах
        - normalize: нормализация громкости (True/False)
        - speed: изменение скорости (1.0 = нормальная, 2.0 = в 2 раза быстрее)
        """
        if not self.is_available():
            return ConversionResult(
                success=False,
                error_message="Audio engine недоступен",
                output_path=None
            )
        
        try:
            from pydub import AudioSegment
            from pydub.effects import normalize as normalize_audio
            
            # Читаем входной файл
            audio = AudioSegment.from_file(input_file)
            
            # Применяем параметры обработки
            bitrate = kwargs.get('bitrate', '192k')
            sample_rate = kwargs.get('sample_rate')
            channels = kwargs.get('channels')
            
            # Изменяем параметры если нужно
            if sample_rate:
                audio = audio.set_frame_rate(int(sample_rate))
            
            if channels:
                if channels == 1:
                    audio = audio.set_channels(1)  # mono
                elif channels == 2:
                    audio = audio.set_channels(2)  # stereo
            
            # Обрезка аудио
            start_time = kwargs.get('start_time')
            end_time = kwargs.get('end_time')
            
            if start_time is not None:
                start_ms = int(float(start_time) * 1000)
                if start_ms < len(audio):
                    audio = audio[start_ms:]
            
            if end_time is not None:
                end_ms = int(float(end_time) * 1000)
                if end_ms > 0:
                    audio = audio[:end_ms]
            
            # Изменение громкости
            volume_change = kwargs.get('volume_change')
            if volume_change is not None:
                audio = audio + float(volume_change)  # изменение в дБ
            
            # Эффекты плавного появления/исчезновения
            fade_in = kwargs.get('fade_in')
            if fade_in is not None:
                fade_in_ms = int(float(fade_in) * 1000)
                audio = audio.fade_in(fade_in_ms)
            
            fade_out = kwargs.get('fade_out')
            if fade_out is not None:
                fade_out_ms = int(float(fade_out) * 1000)
                audio = audio.fade_out(fade_out_ms)
            
            # Нормализация
            if kwargs.get('normalize', False):
                audio = normalize_audio(audio)
            
            # Изменение скорости
            speed = kwargs.get('speed')
            if speed is not None and speed != 1.0:
                # Изменяем скорость через изменение frame_rate
                new_sample_rate = int(audio.frame_rate * speed)
                audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
                audio = audio.set_frame_rate(audio.frame_rate)
            
            # Определяем выходной формат
            if not output_format:
                output_format = 'mp3'
            
            # Экспортируем файл
            export_params = {'format': output_format}
            
            if output_format == 'mp3':
                export_params['bitrate'] = bitrate
                export_params['parameters'] = ["-q:a", "2"]  # высокое качество VBR
            elif output_format == 'flac':
                export_params['parameters'] = ["-compression_level", "8"]
            elif output_format == 'ogg':
                export_params['parameters'] = ["-q:a", "6"]  # качество OGG
            
            audio.export(output_path, **export_params)
            
            # Собираем метаданные
            metadata = {
                'duration': len(audio) / 1000.0,  # в секундах
                'channels': audio.channels,
                'frame_rate': audio.frame_rate,
                'sample_width': audio.sample_width,
                'format': output_format,
                'bitrate': bitrate,
                'rms': audio.rms,
                'dBFS': audio.dBFS,
                'max_amplitude': audio.max
            }
            
            return ConversionResult(
                success=True,
                output_path=output_path,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            return ConversionResult(
                success=False,
                error_message=f"Ошибка конвертации аудио: {str(e)}",
                output_path=None
            )
    
    def extract_audio_from_video(self, video_file, output_path: str, **kwargs) -> ConversionResult:
        """
        Извлекает аудио дорожку из видео файла.
        """
        try:
            from pydub import AudioSegment
            
            # Извлекаем аудио из видео
            audio = AudioSegment.from_file(video_file)
            
            # Применяем те же параметры обработки что и в convert
            return self.convert(
                audio, 
                output_path, 
                output_format=kwargs.get('output_format', 'mp3'),
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Audio extraction error: {e}")
            return ConversionResult(
                success=False,
                error_message=f"Ошибка извлечения аудио: {str(e)}",
                output_path=None
            )
    
    def merge_audio_files(self, audio_files: List, output_path: str, **kwargs) -> ConversionResult:
        """
        Объединяет несколько аудио файлов в один.
        """
        try:
            from pydub import AudioSegment
            
            combined = AudioSegment.empty()
            
            for audio_file in audio_files:
                audio = AudioSegment.from_file(audio_file)
                combined += audio
            
            # Экспортируем объединённый файл
            output_format = kwargs.get('output_format', 'mp3')
            bitrate = kwargs.get('bitrate', '192k')
            
            export_params = {'format': output_format}
            if output_format == 'mp3':
                export_params['bitrate'] = bitrate
            
            combined.export(output_path, **export_params)
            
            return ConversionResult(
                success=True,
                output_path=output_path,
                metadata={
                    'duration': len(combined) / 1000.0,
                    'channels': combined.channels,
                    'frame_rate': combined.frame_rate,
                    'format': output_format,
                    'files_merged': len(audio_files)
                }
            )
            
        except Exception as e:
            logger.error(f"Audio merge error: {e}")
            return ConversionResult(
                success=False,
                error_message=f"Ошибка объединения аудио: {str(e)}",
                output_path=None
            )
    
    def speech_to_text(self, audio_file, output_path: str = None, **kwargs) -> ConversionResult:
        """
        Распознаёт речь из аудио файла и конвертирует в текст.
        
        Поддерживаемые параметры:
        - language: код языка для распознавания (например, 'ru-RU', 'en-US')
        - engine: движок распознавания ('whisper', 'speech_recognition', 'vosk')
        - model_size: размер модели для Whisper ('tiny', 'base', 'small', 'medium', 'large')
        - output_format: формат вывода ('txt', 'json', 'srt', 'vtt')
        - timestamps: добавить временные метки (True/False)
        - confidence_threshold: порог уверенности для фильтрации результатов
        """
        if not self.is_available():
            return ConversionResult(
                success=False,
                error_message="Audio engine недоступен для распознавания речи",
                output_path=None
            )
        
        try:
            # Получаем параметры
            language = kwargs.get('language', 'ru')  # по умолчанию русский
            engine = kwargs.get('engine', 'whisper')  # предпочитаемый движок
            model_size = kwargs.get('model_size', 'base')
            output_format = kwargs.get('output_format', 'txt')
            timestamps = kwargs.get('timestamps', False)
            
            # Определяем выходной путь если не указан
            if not output_path:
                import tempfile
                output_path = tempfile.mktemp(suffix=f'.{output_format}')
            
            # Пробуем использовать Whisper (наиболее точный)
            if engine == 'whisper' or engine == 'auto':
                try:
                    result = self._whisper_speech_to_text(
                        audio_file, output_path, language, model_size, 
                        output_format, timestamps, **kwargs
                    )
                    if result.success:
                        return result
                except Exception as e:
                    logger.warning(f"Whisper failed, trying fallback: {e}")
            
            # Fallback к speech_recognition
            if engine == 'speech_recognition' or engine == 'auto':
                try:
                    result = self._speech_recognition_stt(
                        audio_file, output_path, language, output_format, **kwargs
                    )
                    if result.success:
                        return result
                except Exception as e:
                    logger.warning(f"SpeechRecognition failed: {e}")
            
            # Если все методы не сработали
            return ConversionResult(
                success=False,
                error_message="Не удалось распознать речь: все движки недоступны",
                output_path=None
            )
            
        except Exception as e:
            logger.error(f"Speech to text error: {e}")
            return ConversionResult(
                success=False,
                error_message=f"Ошибка распознавания речи: {str(e)}",
                output_path=None
            )
    
    def _whisper_speech_to_text(self, audio_file, output_path, language, model_size, 
                               output_format, timestamps, **kwargs):
        """
        Распознавание речи с помощью OpenAI Whisper.
        """
        try:
            import whisper
            import json
            
            # Загружаем модель Whisper
            model = whisper.load_model(model_size)
            
            # Конвертируем аудио в формат, понятный Whisper
            from pydub import AudioSegment
            import tempfile
            
            # Загружаем и конвертируем аудио в WAV 16кГц моно
            audio = AudioSegment.from_file(audio_file)
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                audio.export(temp_wav.name, format="wav")
                temp_wav_path = temp_wav.name
            
            try:
                # Выполняем распознавание
                result = model.transcribe(
                    temp_wav_path,
                    language=language if language != 'auto' else None,
                    task="transcribe",
                    verbose=False
                )
                
                # Сохраняем результат в зависимости от формата
                if output_format == 'json':
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                
                elif output_format == 'srt':
                    self._write_srt(result['segments'], output_path)
                
                elif output_format == 'vtt':
                    self._write_vtt(result['segments'], output_path)
                
                else:  # txt format
                    text_content = result['text']
                    if timestamps and 'segments' in result:
                        # Добавляем временные метки
                        text_with_timestamps = []
                        for segment in result['segments']:
                            start_time = self._format_timestamp(segment['start'])
                            text_with_timestamps.append(f"[{start_time}] {segment['text']}")
                        text_content = '\n'.join(text_with_timestamps)
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                
                # Собираем метаданные
                metadata = {
                    'engine': 'whisper',
                    'model_size': model_size,
                    'language': result.get('language', language),
                    'duration': len(audio) / 1000.0,
                    'text_length': len(result['text']),
                    'segments_count': len(result.get('segments', [])),
                    'confidence': self._calculate_avg_confidence(result.get('segments', []))
                }
                
                return ConversionResult(
                    success=True,
                    output_path=output_path,
                    metadata=metadata
                )
                
            finally:
                # Удаляем временный файл
                import os
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass
                    
        except ImportError:
            raise Exception("Whisper не установлен. Установите: pip install openai-whisper")
        except Exception as e:
            raise Exception(f"Ошибка Whisper: {str(e)}")
    
    def _speech_recognition_stt(self, audio_file, output_path, language, output_format, **kwargs):
        """
        Распознавание речи с помощью SpeechRecognition + Google API.
        """
        try:
            import speech_recognition as sr
            from pydub import AudioSegment
            import tempfile
            import json
            
            # Конвертируем в WAV
            audio = AudioSegment.from_file(audio_file)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                audio.export(temp_wav.name, format="wav")
                temp_wav_path = temp_wav.name
            
            try:
                # Инициализируем распознаватель
                r = sr.Recognizer()
                
                # Загружаем аудио
                with sr.AudioFile(temp_wav_path) as source:
                    audio_data = r.record(source)
                
                # Распознаём речь
                try:
                    # Пробуем Google API
                    text = r.recognize_google(audio_data, language=language)
                except sr.RequestError:
                    # Fallback к offline Sphinx
                    try:
                        text = r.recognize_sphinx(audio_data, language=language)
                    except:
                        text = r.recognize_sphinx(audio_data)  # английский по умолчанию
                
                # Сохраняем результат
                if output_format == 'json':
                    result_data = {
                        'text': text,
                        'language': language,
                        'engine': 'speech_recognition',
                        'confidence': None  # SpeechRecognition не предоставляет confidence
                    }
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(result_data, f, ensure_ascii=False, indent=2)
                else:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                
                metadata = {
                    'engine': 'speech_recognition',
                    'language': language,
                    'duration': len(audio) / 1000.0,
                    'text_length': len(text)
                }
                
                return ConversionResult(
                    success=True,
                    output_path=output_path,
                    metadata=metadata
                )
                
            finally:
                import os
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass
                    
        except ImportError:
            raise Exception("SpeechRecognition не установлен. Установите: pip install SpeechRecognition")
        except Exception as e:
            raise Exception(f"Ошибка SpeechRecognition: {str(e)}")
    
    def _write_srt(self, segments, output_path):
        """Записывает субтитры в формате SRT."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, 1):
                start_time = self._format_srt_timestamp(segment['start'])
                end_time = self._format_srt_timestamp(segment['end'])
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text'].strip()}\n\n")
    
    def _write_vtt(self, segments, output_path):
        """Записывает субтитры в формате WebVTT."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for segment in segments:
                start_time = self._format_vtt_timestamp(segment['start'])
                end_time = self._format_vtt_timestamp(segment['end'])
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text'].strip()}\n\n")
    
    def _format_timestamp(self, seconds):
        """Форматирует временную метку для обычного текста."""
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _format_srt_timestamp(self, seconds):
        """Форматирует временную метку для SRT."""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def _format_vtt_timestamp(self, seconds):
        """Форматирует временную метку для WebVTT."""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:03d}"
    
    def _calculate_avg_confidence(self, segments):
        """Вычисляет среднюю уверенность для сегментов Whisper."""
        if not segments:
            return None
        
        confidences = []
        for segment in segments:
            # В Whisper нет прямого поля confidence, но можно использовать 
            # avg_logprob или no_speech_prob для оценки
            if 'avg_logprob' in segment:
                # Конвертируем логарифмическую вероятность в примерный confidence
                confidence = max(0, min(1, (segment['avg_logprob'] + 1.0)))
                confidences.append(confidence)
        
        return sum(confidences) / len(confidences) if confidences else None
