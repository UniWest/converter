import os
import tempfile
import logging
import subprocess
import json
import shutil
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np

# Условные импорты Celery
try:
    from celery import Celery, current_task
    from celery.exceptions import Ignore
    CELERY_AVAILABLE = True
except ImportError:
    # Celery недоступен - создаем заглушки
    Celery = None
    current_task = None
    Ignore = Exception
    CELERY_AVAILABLE = False
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

# Условные импорты для обработки изображений
try:
    from PIL import Image, ImageSequence
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageSequence = None

# Условные импорты для аудио обработки
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None

try:
    import pydub
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    pydub = None
    AudioSegment = None
    split_on_silence = None

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False
    nr = None

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    WhisperModel = None


# Логирование
logger = logging.getLogger(__name__)

# Создаем Celery приложение (только если Celery доступен)
if CELERY_AVAILABLE:
    app = Celery('converter_site')
    
    # Конфигурация
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()
else:
    app = None

# Константы
MAX_AUDIO_DURATION = 3600  # 1 час в секундах
MAX_IMAGE_COUNT = 100
TEMP_DIR = os.path.join(settings.BASE_DIR, 'temp')


def ensure_temp_dir():
    """Убеждаемся, что временная папка существует."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    return TEMP_DIR


def cleanup_temp_files(*file_paths):
    """Безопасно удаляет временные файлы."""
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Удален временный файл: {file_path}")
            except OSError as e:
                logger.warning(f"Не удалось удалить файл {file_path}: {e}")


# Условный декоратор для задачи Celery
if CELERY_AVAILABLE and app:
    @app.task(bind=True, time_limit=7200, soft_time_limit=6600)
    def convert_audio_to_text(self, audio_file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        return _convert_audio_to_text_impl(self, audio_file_path, options)
else:
    def convert_audio_to_text(audio_file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        # Заглушка для работы без Celery
        class MockTask:
            def update_state(self, state=None, meta=None):
                pass
        mock_task = MockTask()
        return _convert_audio_to_text_impl(mock_task, audio_file_path, options)

def _convert_audio_to_text_impl(self, audio_file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Расширенная Celery-задача для конвертации аудио в текст (Speech-to-Text).
    
    Поддерживает:
    1. Предобработка: нормализация, HP/LP фильтры, сегментация через split_on_silence
    2. Транскрибация: faster-whisper (batch по сегментам) или Google Speech Recognition  
    3. Прогресс: update_state с метаданными progress/total
    4. Сборка результатов: генерация TXT/SRT/JSON, сохранение в MEDIA/temp
    5. Удаление временных файлов после завершения
    
    Args:
        audio_file_path: Путь к исходному аудиофайлу
        options: Словарь с параметрами обработки:
            - language: код языка ('ru-RU', 'en-US' или 'auto')
            - output_format: формат результата ('txt', 'srt', 'json')
            - quality: качество обработки ('fast', 'standard', 'high')
            - enhance_speech: улучшение качества звука (bool)
            - remove_silence: удаление пауз через сегментацию (bool)
            - use_whisper: принудительно использовать Whisper (bool)
    
    Returns:
        Dict с результатами:
        {
            'success': bool,
            'task_id': str,
            'transcription': str,
            'output_files': {
                'txt_url': str,
                'srt_url': str, 
                'json_url': str
            },
            'duration': float,
            'language': str,
            'segments_count': int,
            'processing_time': float,
            'engine_used': str,
            'error': str | None
        }
    """
    # Проверяем доступность необходимых библиотек
    if not PYDUB_AVAILABLE:
        error_msg = "Аудио обработка недоступна: не установлен pydub. Установите: pip install pydub"
        logger.error(error_msg)
        return {
            'success': False,
            'task_id': 'unavailable',
            'error': error_msg,
            'transcription': None,
            'output_files': {'txt_url': None, 'srt_url': None, 'json_url': None},
            'duration': None,
            'language': options.get('language', 'auto'),
            'segments_count': 0,
            'processing_time': None,
            'engine_used': None
        }
    
    if not SPEECH_RECOGNITION_AVAILABLE and not FASTER_WHISPER_AVAILABLE:
        error_msg = "Распознавание речи недоступно: не установлены speech_recognition и faster-whisper. Установите: pip install SpeechRecognition"
        logger.error(error_msg)
        return {
            'success': False,
            'task_id': 'unavailable',
            'error': error_msg,
            'transcription': None,
            'output_files': {'txt_url': None, 'srt_url': None, 'json_url': None},
            'duration': None,
            'language': options.get('language', 'auto'),
            'segments_count': 0,
            'processing_time': None,
            'engine_used': None
        }
    
    task_id = getattr(self, 'request', type('obj', (object,), {'id': 'mock-task-id'})).id
    start_time = datetime.now()
    logger.info(f"[{task_id}] Начало расширенной транскрипции аудио")
    
    temp_files = []
    segments = []
    result = {
        'success': False,
        'task_id': task_id,
        'transcription': None,
        'output_files': {'txt_url': None, 'srt_url': None, 'json_url': None},
        'duration': None,
        'language': options.get('language', 'auto'),
        'segments_count': 0,
        'processing_time': None,
        'engine_used': None,
        'error': None
    }
    
    try:
        # Этап 1: Предобработка - загрузка и проверка аудио
        self.update_state(
            state='PROGRESS', 
            meta={'progress': 5, 'total': 100, 'status': 'Загрузка аудиофайла...'}
        )
        
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Аудиофайл не найден: {audio_file_path}")
        
        # Загружаем исходное аудио
        logger.info(f"[{task_id}] Загрузка аудио из: {audio_file_path}")
        audio_segment = AudioSegment.from_file(audio_file_path)
        duration_seconds = len(audio_segment) / 1000.0
        result['duration'] = duration_seconds
        
        # Проверка максимальной длительности
        max_duration = getattr(settings, 'AUDIO_MAX_DURATION', 3600)
        if duration_seconds > max_duration:
            raise ValueError(
                f"Аудиофайл слишком длинный: {duration_seconds:.1f}с "
                f"(максимум {max_duration}с)"
            )
        
        logger.info(f"[{task_id}] Длительность аудио: {duration_seconds:.1f} секунд")
        
        # Этап 2: Предобработка - нормализация и фильтрация
        self.update_state(
            state='PROGRESS',
            meta={'progress': 15, 'total': 100, 'status': 'Предобработка аудио...'}
        )
        
        processed_audio = preprocess_audio(
            audio_segment, 
            options, 
            lambda status: self.update_state(
                state='PROGRESS',
                meta={'progress': 15, 'total': 100, 'status': status}
            )
        )
        
        # Этап 3: Сегментация (если включена)
        if options.get('remove_silence', False):
            self.update_state(
                state='PROGRESS',
                meta={'progress': 25, 'total': 100, 'status': 'Сегментация аудио...'}
            )
            
            segments = segment_audio_by_silence(processed_audio, options)
            result['segments_count'] = len(segments)
            logger.info(f"[{task_id}] Создано сегментов: {len(segments)}")
        else:
            # Используем весь аудиофайл как один сегмент
            segments = [processed_audio]
            result['segments_count'] = 1
        
        # Этап 4: Транскрибация
        engine = determine_stt_engine(options, duration_seconds)
        result['engine_used'] = engine
        
        self.update_state(
            state='PROGRESS',
            meta={'progress': 40, 'total': 100, 'status': f'Транскрибация ({engine})...'}
        )
        
        # Транскрибируем сегменты
        transcription_results = transcribe_audio_segments(
            segments, engine, options, task_id, temp_files,
            progress_callback=lambda p: self.update_state(
                state='PROGRESS',
                meta={'progress': 40 + int(p * 0.4), 'total': 100, 'status': 'Транскрибация...'}
            )
        )
        
        if not transcription_results:
            raise ValueError("Не удалось распознать речь в аудиофайле")
        
        # Собираем итоговый текст
        full_text = assemble_transcription(transcription_results)
        result['transcription'] = full_text
        
        # Этап 5: Генерация выходных файлов
        self.update_state(
            state='PROGRESS',
            meta={'progress': 85, 'total': 100, 'status': 'Создание файлов результата...'}
        )
        
        result['output_files'] = generate_output_files(
            transcription_results, duration_seconds, task_id, temp_files
        )
        
        # Этап 6: Финализация
        processing_time = (datetime.now() - start_time).total_seconds()
        result['processing_time'] = processing_time
        result['success'] = True
        
        self.update_state(
            state='SUCCESS', 
            meta={'progress': 100, 'total': 100, 'status': 'Транскрибация завершена!'}
        )
        
        logger.info(
            f"[{task_id}] Транскрибация завершена успешно. "
            f"Время обработки: {processing_time:.1f}с, движок: {engine}"
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{task_id}] Ошибка транскрипции: {error_msg}\n{traceback.format_exc()}")
        
        result['error'] = error_msg
        self.update_state(state='FAILURE', meta={'error': error_msg})
        
        # Очистка временных файлов при ошибке
        cleanup_temp_files(*temp_files)
        raise Ignore()
    
    finally:
        # Очистка сегментов из памяти
        del segments
        if 'audio_segment' in locals():
            del audio_segment
        if 'processed_audio' in locals():
            del processed_audio
    
    return result


# ===========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ STT
# ===========================

def preprocess_audio(audio_segment: AudioSegment, options: Dict[str, Any], status_callback) -> AudioSegment:
    """
    Предобработка аудио: нормализация, фильтрация, шумоподавление.
    
    Args:
        audio_segment: Исходный аудио сегмент
        options: Опции обработки
        status_callback: Функция для обновления статуса
    
    Returns:
        Обработанный аудио сегмент
    """
    processed = audio_segment
    
    # Конвертируем в моно 16кГц если нужно
    if processed.channels > 1:
        status_callback('Конвертация в моно...')
        processed = processed.set_channels(1)
    
    if processed.frame_rate != 16000:
        status_callback('Изменение частоты дискретизации...')
        processed = processed.set_frame_rate(16000)
    
    # Нормализация громкости
    if options.get('enhance_speech', False) or getattr(settings, 'AUDIO_PREPROCESSING', {}).get('normalize', False):
        status_callback('Нормализация громкости...')
        processed = processed.normalize()
    
    # Фильтрация частот для улучшения речи
    if options.get('enhance_speech', False):
        status_callback('Фильтрация частот...')
        
        # Получаем настройки из конфигурации
        audio_config = getattr(settings, 'AUDIO_PREPROCESSING', {})
        high_pass = audio_config.get('high_pass_filter', 300)
        low_pass = audio_config.get('low_pass_filter', 3400)
        
        # Применяем фильтры
        processed = processed.high_pass_filter(high_pass)
        processed = processed.low_pass_filter(low_pass)
    
    # Шумоподавление с помощью noisereduce (если доступно)
    if options.get('enhance_speech', False) and 'noisereduce' in globals():
        try:
            status_callback('Подавление шума...')
            
            # Конвертируем в numpy массив
            samples = np.array(processed.get_array_of_samples())
            if processed.sample_width == 2:
                samples = samples.astype(np.float32) / 32768.0
            elif processed.sample_width == 4:
                samples = samples.astype(np.float32) / 2147483648.0
            
            # Применяем шумоподавление
            cleaned_samples = nr.reduce_noise(
                y=samples, 
                sr=processed.frame_rate,
                stationary=True,
                prop_decrease=0.8
            )
            
            # Конвертируем обратно
            if processed.sample_width == 2:
                cleaned_samples = (cleaned_samples * 32768.0).astype(np.int16)
            elif processed.sample_width == 4:
                cleaned_samples = (cleaned_samples * 2147483648.0).astype(np.int32)
            
            processed = AudioSegment(
                cleaned_samples.tobytes(),
                frame_rate=processed.frame_rate,
                sample_width=processed.sample_width,
                channels=1
            )
            
        except Exception as e:
            logger.warning(f"Не удалось применить шумоподавление: {e}")
    
    return processed


def segment_audio_by_silence(audio_segment: AudioSegment, options: Dict[str, Any]) -> List[AudioSegment]:
    """
    Сегментация аудио по паузам с использованием split_on_silence.
    
    Args:
        audio_segment: Аудио для сегментации
        options: Опции сегментации
    
    Returns:
        Список аудио сегментов
    """
    audio_config = getattr(settings, 'AUDIO_PREPROCESSING', {})
    
    # Параметры сегментации
    min_silence_len = audio_config.get('min_silence_len', 1000)  # мс
    silence_thresh = audio_segment.dBFS + audio_config.get('silence_threshold', -40)  # dBFS
    keep_silence = audio_config.get('keep_silence', 500)  # мс
    
    logger.info(f"Сегментация с параметрами: min_silence={min_silence_len}мс, thresh={silence_thresh}dBFS")
    
    # Разбиваем на сегменты
    chunks = split_on_silence(
        audio_segment,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=keep_silence,
        seek_step=100
    )
    
    if not chunks:
        logger.warning("Сегментация не дала результатов, используем исходное аудио")
        return [audio_segment]
    
    # Фильтруем слишком короткие сегменты (менее 0.5 секунды)
    min_segment_len = 500  # мс
    filtered_chunks = [chunk for chunk in chunks if len(chunk) >= min_segment_len]
    
    if not filtered_chunks:
        logger.warning("Все сегменты слишком короткие, используем исходное аудио")
        return [audio_segment]
    
    logger.info(f"Создано {len(filtered_chunks)} сегментов после фильтрации")
    return filtered_chunks


def determine_stt_engine(options: Dict[str, Any], duration_seconds: float) -> str:
    """
    Определяет, какой движок STT использовать.
    
    Args:
        options: Опции пользователя
        duration_seconds: Длительность аудио
    
    Returns:
        Название движка: 'whisper' или 'google'
    """
    # Принудительный выбор пользователя
    if options.get('use_whisper', False):
        if not FASTER_WHISPER_AVAILABLE:
            logger.warning("faster-whisper недоступен, используем Google")
            return 'google'
        return 'whisper'
    
    # Настройка из конфигурации
    stt_engine = getattr(settings, 'STT_ENGINE', 'whisper')
    
    if stt_engine == 'whisper' and FASTER_WHISPER_AVAILABLE:
        return 'whisper'
    
    # Fallback для коротких файлов (<2 мин) - используем Google
    if duration_seconds < 120:  # 2 минуты
        return 'google'
    
    # По умолчанию Google если Whisper недоступен
    if not FASTER_WHISPER_AVAILABLE:
        return 'google'
    
    return 'whisper'


def transcribe_audio_segments(
    segments: List[AudioSegment], 
    engine: str, 
    options: Dict[str, Any], 
    task_id: str,
    temp_files: List[str],
    progress_callback
) -> List[Dict[str, Any]]:
    """
    Транскрибирует список аудио сегментов с использованием выбранного движка.
    
    Args:
        segments: Список аудио сегментов
        engine: Движок STT ('whisper' или 'google')
        options: Опции транскрибации
        task_id: ID задачи для уникальности имен файлов
        temp_files: Список для отслеживания временных файлов
        progress_callback: Функция обратного вызова для прогресса
    
    Returns:
        Список результатов транскрибации с временными метками
    """
    results = []
    total_segments = len(segments)
    current_time = 0.0
    
    logger.info(f"[{task_id}] Транскрибация {total_segments} сегментов с помощью {engine}")
    
    if engine == 'whisper' and FASTER_WHISPER_AVAILABLE:
        results = transcribe_with_whisper(segments, options, task_id, temp_files, progress_callback)
    else:
        results = transcribe_with_google(segments, options, task_id, temp_files, progress_callback)
    
    return results


def transcribe_with_whisper(
    segments: List[AudioSegment], 
    options: Dict[str, Any], 
    task_id: str,
    temp_files: List[str],
    progress_callback
) -> List[Dict[str, Any]]:
    """
    Транскрибация с помощью faster-whisper.
    """
    logger.info(f"[{task_id}] Использование faster-whisper для транскрибации")
    
    # Получаем настройки Whisper
    model_name = getattr(settings, 'WHISPER_MODEL', 'base')
    device = getattr(settings, 'WHISPER_DEVICE', 'auto')
    compute_type = getattr(settings, 'WHISPER_COMPUTE_TYPE', 'int8')
    
    # Определяем язык
    language_code = options.get('language', 'auto')
    if language_code == 'auto':
        language = None  # Whisper автоопределение
    elif language_code.startswith('ru'):
        language = 'ru'
    elif language_code.startswith('en'):
        language = 'en'
    else:
        # Пытаемся извлечь код языка
        language = language_code.split('-')[0] if '-' in language_code else language_code
    
    try:
        # Инициализируем модель Whisper
        logger.info(f"[{task_id}] Загрузка модели Whisper: {model_name} на {device}")
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        
        results = []
        current_time = 0.0
        
        for i, segment in enumerate(segments):
            segment_duration = len(segment) / 1000.0
            
            # Обновляем прогресс
            progress = i / len(segments)
            progress_callback(progress)
            
            # Сохраняем сегмент во временный файл
            segment_path = os.path.join(ensure_temp_dir(), f"segment_{task_id}_{i}.wav")
            temp_files.append(segment_path)
            
            segment.export(segment_path, format="wav")
            
            try:
                # Транскрибируем сегмент
                segments_result, info = model.transcribe(
                    segment_path, 
                    language=language,
                    beam_size=5,
                    best_of=5,
                    temperature=0.0
                )
                
                # Собираем текст из всех подсегментов
                segment_text = ' '.join([s.text.strip() for s in segments_result])
                
                if segment_text:
                    results.append({
                        'text': segment_text,
                        'start': current_time,
                        'end': current_time + segment_duration,
                        'language': info.language,
                        'confidence': getattr(info, 'language_probability', 0.9)
                    })
                    
                    logger.debug(f"[{task_id}] Сегмент {i+1}: '{segment_text[:50]}...'")
                
            except Exception as e:
                logger.error(f"[{task_id}] Ошибка транскрибации сегмента {i}: {e}")
                # Добавляем пустой результат чтобы не нарушить временную последовательность
                results.append({
                    'text': '',
                    'start': current_time,
                    'end': current_time + segment_duration,
                    'language': language or 'unknown',
                    'confidence': 0.0
                })
            
            current_time += segment_duration
            
            # Удаляем временный файл сегмента
            cleanup_temp_files(segment_path)
            temp_files.remove(segment_path)
        
        logger.info(f"[{task_id}] Whisper транскрибация завершена: {len(results)} сегментов")
        return results
        
    except Exception as e:
        logger.error(f"[{task_id}] Ошибка инициализации Whisper: {e}")
        # Fallback на Google
        logger.info(f"[{task_id}] Переключение на Google Speech Recognition")
        return transcribe_with_google(segments, options, task_id, temp_files, progress_callback)


def transcribe_with_google(
    segments: List[AudioSegment], 
    options: Dict[str, Any], 
    task_id: str,
    temp_files: List[str],
    progress_callback
) -> List[Dict[str, Any]]:
    """
    Транскрибация с помощью Google Speech Recognition.
    """
    logger.info(f"[{task_id}] Использование Google Speech Recognition для транскрибации")
    
    # Настройка языка
    language_code = options.get('language', 'ru-RU')
    if language_code == 'auto':
        language_code = 'ru-RU'  # По умолчанию русский
    
    results = []
    current_time = 0.0
    
    for i, segment in enumerate(segments):
        segment_duration = len(segment) / 1000.0
        
        # Обновляем прогресс
        progress = i / len(segments)
        progress_callback(progress)
        
        # Сохраняем сегмент во временный файл
        segment_path = os.path.join(ensure_temp_dir(), f"segment_{task_id}_{i}.wav")
        temp_files.append(segment_path)
        
        segment.export(segment_path, format="wav", parameters=["-ar", "16000", "-ac", "1"])
        
        try:
            # Транскрибируем сегмент
            segment_text = perform_speech_recognition(
                segment_path, 
                language_code, 
                options.get('quality', 'standard')
            )
            
            if segment_text:
                results.append({
                    'text': segment_text,
                    'start': current_time,
                    'end': current_time + segment_duration,
                    'language': language_code,
                    'confidence': 0.9  # Google не предоставляет точную оценку
                })
                
                logger.debug(f"[{task_id}] Сегмент {i+1}: '{segment_text[:50]}...'")
            
        except Exception as e:
            logger.error(f"[{task_id}] Ошибка транскрибации сегмента {i}: {e}")
            # Добавляем пустой результат
            results.append({
                'text': '',
                'start': current_time,
                'end': current_time + segment_duration,
                'language': language_code,
                'confidence': 0.0
            })
        
        current_time += segment_duration
        
        # Удаляем временный файл сегмента
        cleanup_temp_files(segment_path)
        temp_files.remove(segment_path)
    
    logger.info(f"[{task_id}] Google транскрибация завершена: {len(results)} сегментов")
    return results


def assemble_transcription(transcription_results: List[Dict[str, Any]]) -> str:
    """
    Собирает итоговый текст из результатов транскрибации сегментов.
    """
    if not transcription_results:
        return ''
    
    # Фильтруем пустые результаты и объединяем текст
    texts = [result['text'].strip() for result in transcription_results if result['text'].strip()]
    
    if not texts:
        return ''
    
    # Объединяем с пробелами, избегая двойных пробелов
    full_text = ' '.join(texts)
    full_text = ' '.join(full_text.split())  # Убираем лишние пробелы
    
    return full_text


def generate_output_files(
    transcription_results: List[Dict[str, Any]], 
    total_duration: float, 
    task_id: str,
    temp_files: List[str]
) -> Dict[str, str]:
    """
    Генерирует выходные файлы в форматах TXT, SRT, JSON.
    
    Returns:
        Словарь с URL-ами файлов
    """
    logger.info(f"[{task_id}] Генерация выходных файлов")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = ensure_temp_dir()
    
    # Собираем полный текст
    full_text = assemble_transcription(transcription_results)
    
    output_files = {}
    
    # Генерируем TXT файл
    txt_filename = f"transcription_{task_id}_{timestamp}.txt"
    txt_path = os.path.join(temp_dir, txt_filename)
    temp_files.append(txt_path)
    
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    output_files['txt_url'] = f"/media/temp/{txt_filename}"
    
    # Генерируем SRT файл
    srt_filename = f"transcription_{task_id}_{timestamp}.srt"
    srt_path = os.path.join(temp_dir, srt_filename)
    temp_files.append(srt_path)
    
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(generate_srt_content(transcription_results))
    
    output_files['srt_url'] = f"/media/temp/{srt_filename}"
    
    # Генерируем JSON файл
    json_filename = f"transcription_{task_id}_{timestamp}.json"
    json_path = os.path.join(temp_dir, json_filename)
    temp_files.append(json_path)
    
    json_data = {
        'text': full_text,
        'duration': total_duration,
        'timestamp': datetime.now().isoformat(),
        'segments': transcription_results,
        'segments_count': len(transcription_results),
        'language': transcription_results[0]['language'] if transcription_results else 'unknown'
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    output_files['json_url'] = f"/media/temp/{json_filename}"
    
    logger.info(f"[{task_id}] Созданы файлы: TXT, SRT, JSON")
    return output_files


def generate_srt_content(transcription_results: List[Dict[str, Any]]) -> str:
    """
    Генерирует содержимое SRT файла из результатов транскрибации.
    """
    if not transcription_results:
        return ''
    
    srt_lines = []
    subtitle_num = 1
    
    for result in transcription_results:
        if not result['text'].strip():
            continue
        
        start_time = seconds_to_srt_time(result['start'])
        end_time = seconds_to_srt_time(result['end'])
        
        srt_lines.append(f"{subtitle_num}")
        srt_lines.append(f"{start_time} --> {end_time}")
        srt_lines.append(result['text'].strip())
        srt_lines.append("")  # Пустая строка между субтитрами
        
        subtitle_num += 1
    
    return '\n'.join(srt_lines)


def perform_speech_recognition(audio_path: str, language: str, quality: str, engine: str = 'google') -> str:
    """
    Выполняет распознавание речи из аудиофайла с учетом ограничений по длительности.
    
    Args:
        audio_path: Путь к WAV файлу
        language: Язык распознавания (формат locale)
        quality: Качество распознавания
        engine: Движок распознавания ('whisper', 'google')
    
    Returns:
        Распознанный текст
    """
    # Проверяем доступность speech_recognition
    if not SPEECH_RECOGNITION_AVAILABLE or sr is None:
        error_msg = "Распознавание речи недоступно: библиотека speech_recognition не установлена. Установите: pip install SpeechRecognition"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Проверяем длительность аудио для Google API
    audio_duration = _get_audio_file_duration(audio_path)
    
    # Google API имеет ограничение ~60 секунд для synchronous requests
    if engine == 'google' and audio_duration > 50:  # Оставляем запас
        logger.warning(f"Аудиофайл слишком длинный для Google API ({audio_duration:.1f}с), будет обрезан")
        # Для длинных файлов используем только первые 50 секунд как fallback
        return _recognize_google_with_duration_limit(audio_path, language, quality, 50)
    
    recognizer = sr.Recognizer()
    
    # Настройки качества
    if quality == 'high':
        recognizer.energy_threshold = 200
        recognizer.dynamic_energy_threshold = True
        recognizer.dynamic_energy_adjustment_damping = 0.15
        recognizer.dynamic_energy_ratio = 1.5
        recognizer.pause_threshold = 0.8
        recognizer.operation_timeout = None
        recognizer.phrase_threshold = 0.3
        recognizer.non_speaking_duration = 0.5
    elif quality == 'fast':
        recognizer.energy_threshold = 4000
        recognizer.pause_threshold = 0.5
        recognizer.phrase_threshold = 0.5
        recognizer.operation_timeout = 15  # Увеличено для надежности
    else:  # standard
        recognizer.energy_threshold = 300
        recognizer.pause_threshold = 0.8
        recognizer.phrase_threshold = 0.3
        recognizer.operation_timeout = 30  # Добавлен таймаут
    
    try:
        with sr.AudioFile(audio_path) as source:
            # Записываем аудио данные
            logger.info(f"Загружаем аудио: {audio_path}, длительность: {audio_duration:.1f}с")
            audio_data = recognizer.record(source)
            
            # Распознаем речь используя Google Speech Recognition
            logger.info(f"Начинаем распознавание через Google API, язык: {language}")
            text = recognizer.recognize_google(
                audio_data, 
                language=language,
                show_all=False
            )
            
            logger.info(f"Распознанный текст ({len(text)} символов): '{text[:100]}...'")
            return text.strip()
            
    except sr.UnknownValueError:
        logger.warning("Google API не смог распознать речь в аудиофайле")
        raise ValueError("Не удалось распознать речь в аудиофайле")
    except sr.RequestError as e:
        logger.error(f"Ошибка Google API: {e}")
        raise ValueError(f"Ошибка сервиса распознавания речи: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при распознавании: {e}")
        raise ValueError(f"Ошибка распознавания речи: {e}")


def format_transcription(text: str, format_type: str, duration: float) -> str:
    """
    Форматирует результат транскрипции в нужный формат.
    
    Args:
        text: Распознанный текст
        format_type: Тип формата (txt, srt, json)
        duration: Продолжительность аудио в секундах
    
    Returns:
        Отформатированная строка
    """
    if format_type == 'txt':
        return text
    
    elif format_type == 'srt':
        # Простой SRT формат (весь текст как один субтитр)
        return f"""1
00:00:00,000 --> {seconds_to_srt_time(duration)}
{text}
"""
    
    elif format_type == 'json':
        return json.dumps({
            'text': text,
            'duration': duration,
            'language': 'auto-detected',
            'timestamp': datetime.now().isoformat(),
            'segments': [
                {
                    'start': 0,
                    'end': duration,
                    'text': text
                }
            ]
        }, ensure_ascii=False, indent=2)
    
    return text


def seconds_to_srt_time(seconds: float) -> str:
    """Конвертирует секунды в формат времени SRT."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# Условное создание задачи GIF
if CELERY_AVAILABLE and app:
    @app.task(bind=True, time_limit=1800, soft_time_limit=1500)
    def create_gif_from_images(self, image_paths: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
        return _create_gif_from_images_impl(self, image_paths, options)
else:
    def create_gif_from_images(image_paths: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
        # Заглушка
        class MockTask:
            request = type('obj', (object,), {'id': 'mock-gif-task'})()
            def update_state(self, state=None, meta=None):
                pass
        mock_task = MockTask()
        return _create_gif_from_images_impl(mock_task, image_paths, options)

def _create_gif_from_images_impl(self, image_paths: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Celery задача для создания GIF анимации из набора изображений.
    
    Args:
        image_paths: Список путей к изображениям
        options: Словарь с параметрами создания GIF
    
    Returns:
        Dict с результатами обработки
    """
    # Проверяем доступность необходимых библиотек
    if not PIL_AVAILABLE:
        error_msg = "Обработка изображений недоступна: не установлен PIL/Pillow. Установите: pip install Pillow"
        logger.error(error_msg)
        return {
            'success': False,
            'task_id': 'unavailable',
            'error': error_msg,
            'output_file': None,
            'frame_count': len(image_paths),
            'duration': None,
            'file_size': None
        }
    
    task_id = self.request.id
    logger.info(f"Начало создания GIF из {len(image_paths)} изображений, задача {task_id}")
    
    temp_files = []
    result = {
        'success': False,
        'task_id': task_id,
        'error': None,
        'output_file': None,
        'frame_count': len(image_paths),
        'duration': None,
        'file_size': None
    }
    
    try:
        # Проверяем количество изображений
        if len(image_paths) < 2:
            raise ValueError("Для создания GIF нужно минимум 2 изображения")
        if len(image_paths) > MAX_IMAGE_COUNT:
            raise ValueError(f"Слишком много изображений: {len(image_paths)} (максимум {MAX_IMAGE_COUNT})")
        
        self.update_state(state='PROGRESS', meta={'current': 5, 'total': 100, 'status': 'Загрузка изображений...'})
        
        # Сортировка изображений
        sorted_paths = sort_image_paths(image_paths, options.get('sort_order', 'filename'))
        
        # Эффект пинг-понг (добавляем обратный порядок)
        if options.get('pingpong', False):
            sorted_paths = sorted_paths + sorted_paths[:-1][::-1]
        
        # Загружаем и обрабатываем изображения
        frames = []
        target_size = None
        
        for i, image_path in enumerate(sorted_paths):
            progress = 10 + (i * 60 // len(sorted_paths))
            self.update_state(state='PROGRESS', meta={
                'current': progress, 
                'total': 100, 
                'status': f'Обработка изображения {i+1}/{len(sorted_paths)}...'
            })
            
            if not os.path.exists(image_path):
                logger.warning(f"Изображение не найдено: {image_path}")
                continue
            
            try:
                with Image.open(image_path) as img:
                    # Конвертируем в RGB если нужно
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Определяем размер для первого изображения
                    if target_size is None:
                        target_size = calculate_output_size(img.size, options.get('output_size', '480'))
                    
                    # Изменяем размер изображения
                    if img.size != target_size:
                        img = img.resize(target_size, Image.Resampling.LANCZOS)
                    
                    frames.append(img.copy())
                    
            except Exception as e:
                logger.warning(f"Не удалось обработать изображение {image_path}: {e}")
                continue
        
        if len(frames) < 2:
            raise ValueError("Не удалось загрузить достаточное количество изображений")
        
        # Создание GIF
        self.update_state(state='PROGRESS', meta={'current': 75, 'total': 100, 'status': 'Создание GIF...'})
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"animation_{timestamp}.gif"
        output_path = os.path.join(ensure_temp_dir(), output_filename)
        temp_files.append(output_path)
        
        # Параметры GIF
        frame_duration_ms = int(options.get('frame_duration', 0.5) * 1000)
        loop_count = 0 if options.get('loop', True) else 1
        
        # Оптимизация цветов
        colors = int(options.get('colors', 128))
        
        # Сохраняем GIF
        frames[0].save(
            output_path,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration_ms,
            loop=loop_count,
            optimize=options.get('optimize', True),
            colors=colors
        )
        
        # Получаем информацию о файле
        file_size = os.path.getsize(output_path)
        total_duration = len(frames) * options.get('frame_duration', 0.5)
        
        result.update({
            'output_file': output_path,
            'frame_count': len(frames),
            'duration': total_duration,
            'file_size': file_size,
            'success': True
        })
        
        self.update_state(state='SUCCESS', meta={'current': 100, 'total': 100, 'status': 'GIF создан!'})
        logger.info(f"GIF создан успешно, задача {task_id}: {len(frames)} кадров, {file_size} байт")
        
    except Exception as e:
        logger.error(f"Ошибка создания GIF, задача {task_id}: {str(e)}")
        result['error'] = str(e)
        self.update_state(state='FAILURE', meta={'error': str(e)})
        # Очистка при ошибке
        cleanup_temp_files(*temp_files)
        raise Ignore()
    
    return result


def sort_image_paths(paths: List[str], sort_order: str) -> List[str]:
    """
    Сортирует пути к изображениям согласно выбранному порядку.
    
    Args:
        paths: Список путей к файлам
        sort_order: Тип сортировки ('filename', 'upload', 'reverse')
    
    Returns:
        Отсортированный список путей
    """
    if sort_order == 'filename':
        return sorted(paths, key=lambda x: os.path.basename(x).lower())
    elif sort_order == 'reverse':
        return sorted(paths, key=lambda x: os.path.basename(x).lower(), reverse=True)
    else:  # 'upload' или по умолчанию
        return paths


def calculate_output_size(original_size: tuple, size_option: str) -> tuple:
    """
    Вычисляет размер выходного изображения.
    
    Args:
        original_size: Оригинальный размер (width, height)
        size_option: Опция размера ('original', '320', '480', '720', '1080')
    
    Returns:
        Новый размер (width, height)
    """
    if size_option == 'original':
        return original_size
    
    target_width = int(size_option)
    original_width, original_height = original_size
    
    # Вычисляем пропорциональную высоту
    aspect_ratio = original_height / original_width
    target_height = int(target_width * aspect_ratio)
    
    # Убеждаемся, что размеры четные (требование для некоторых форматов)
    target_width = target_width if target_width % 2 == 0 else target_width - 1
    target_height = target_height if target_height % 2 == 0 else target_height - 1
    
    return (target_width, target_height)


# Условное создание задачи очистки
if CELERY_AVAILABLE and app:
    @app.task
    def cleanup_old_files(days_old: int = 1):
        return _cleanup_old_files_impl(days_old)
else:
    def cleanup_old_files(days_old: int = 1):
        return _cleanup_old_files_impl(days_old)

def _cleanup_old_files_impl(days_old: int = 1):
    """
    Задача для очистки старых временных файлов.
    Запускается по расписанию.
    
    Args:
        days_old: Возраст файлов в днях для удаления
    """
    import time
    
    logger.info(f"Запуск очистки файлов старше {days_old} дней")
    
    if not os.path.exists(TEMP_DIR):
        return
    
    cutoff_time = time.time() - (days_old * 24 * 60 * 60)
    deleted_count = 0
    
    for filename in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, filename)
        try:
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                os.remove(file_path)
                deleted_count += 1
                logger.debug(f"Удален старый файл: {filename}")
        except OSError as e:
            logger.warning(f"Не удалось удалить файл {filename}: {e}")
    
    logger.info(f"Очистка завершена, удалено файлов: {deleted_count}")
    return deleted_count


# Условное создание задачи отмены
if CELERY_AVAILABLE and app:
    @app.task(bind=True)
    def revoke_task(self, task_id: str):
        return _revoke_task_impl(self, task_id)
else:
    def revoke_task(task_id: str):
        # Заглушка
        class MockTask:
            request = type('obj', (object,), {'id': 'mock-revoke-task'})()
        mock_task = MockTask()
        return _revoke_task_impl(mock_task, task_id)

def _revoke_task_impl(self, task_id: str):
    """Отменяет выполнение задачи и очищает ресурсы."""
    try:
        if CELERY_AVAILABLE and app:
            app.control.revoke(task_id, terminate=True)
            logger.info(f"Задача {task_id} отменена")
        else:
            logger.info(f"Celery недоступен, отмена задачи {task_id} игнорируется")
        return True
    except Exception as e:
        logger.error(f"Ошибка отмены задачи {task_id}: {e}")
        return False


# ===========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ АУДИО
# ===========================

def _get_audio_file_duration(audio_path: str) -> float:
    """
    Получает длительность аудиофайла в секундах.
    
    Args:
        audio_path: Путь к аудиофайлу
    
    Returns:
        Длительность в секундах
    """
    try:
        if PYDUB_AVAILABLE and AudioSegment is not None:
            audio_segment = AudioSegment.from_file(audio_path)
            return len(audio_segment) / 1000.0  # конвертируем из мс в с
        else:
            logger.warning("pydub недоступен, возвращаем длительность по умолчанию")
            return 60.0  # возвращаем значение по умолчанию
    except Exception as e:
        logger.warning(f"Не удалось определить длительность аудио {audio_path}: {e}")
        return 60.0  # возвращаем значение по умолчанию


def _recognize_google_with_duration_limit(audio_path: str, language: str, quality: str, max_duration: int) -> str:
    """
    Распознает речь через Google API с ограничением по длительности.
    Для длинных файлов обрабатывает только первую часть.
    
    Args:
        audio_path: Путь к аудиофайлу
        language: Язык распознавания
        quality: Качество распознавания
        max_duration: Максимальная длительность в секундах
    
    Returns:
        Распознанный текст
    """
    if not SPEECH_RECOGNITION_AVAILABLE or sr is None:
        raise ValueError("speech_recognition недоступен")
    
    if not PYDUB_AVAILABLE or AudioSegment is None:
        logger.warning("pydub недоступен, используем файл как есть")
        return perform_speech_recognition(audio_path, language, quality, 'google')
    
    try:
        # Загружаем аудио
        audio_segment = AudioSegment.from_file(audio_path)
        duration_seconds = len(audio_segment) / 1000.0
        
        logger.info(f"Обрезка аудио с {duration_seconds:.1f}с до {max_duration}с")
        
        # Обрезаем до максимальной длительности
        if duration_seconds > max_duration:
            truncated_audio = audio_segment[:max_duration * 1000]  # в мс
        else:
            truncated_audio = audio_segment
        
        # Сохраняем обрезанное аудио во временный файл
        temp_path = audio_path + "_truncated.wav"
        truncated_audio.export(temp_path, format="wav")
        
        try:
            # Распознаем обрезанную версию
            result = perform_speech_recognition(temp_path, language, quality, 'google')
            logger.info(f"Распознавание обрезанного файла завершено: {len(result)} символов")
            return result
        finally:
            # Удаляем временный файл
            cleanup_temp_files(temp_path)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке длинного файла: {e}")
        raise ValueError(f"Ошибка обработки аудио: {e}")

