import os
import uuid
import tempfile
import logging
import math
import json
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from forms import VideoUploadForm
from .models import ConversionTask
from .services import VideoConversionService
from .utils import VideoConverter

logger = logging.getLogger(__name__)


# Helper functions for enhanced audio processing
def apply_noise_reduction(audio, intensity='medium'):
    """
    Apply noise reduction using spectral subtraction technique.
    
    Args:
        audio: AudioSegment object
        intensity: 'light', 'medium', 'strong'
    
    Returns:
        AudioSegment with reduced noise
    """
    try:
        import numpy as np
        from scipy.signal import butter, filtfilt
        
        # Convert audio to numpy array
        samples = np.array(audio.get_array_of_samples())
        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
            samples = np.mean(samples, axis=1)  # Convert to mono
        
        # Normalize to float32
        if audio.sample_width == 2:
            samples = samples.astype(np.float32) / 32768.0
        elif audio.sample_width == 4:
            samples = samples.astype(np.float32) / 2147483648.0
        
        # Apply noise reduction based on intensity
        if intensity == 'light':
            # Simple high-pass filter
            b, a = butter(2, 200, btype='high', fs=audio.frame_rate)
            filtered_samples = filtfilt(b, a, samples)
        elif intensity == 'medium':
            # Bandpass filter for speech frequencies
            b, a = butter(4, [200, 4000], btype='band', fs=audio.frame_rate)
            filtered_samples = filtfilt(b, a, samples)
        elif intensity == 'strong':
            # More aggressive filtering
            b, a = butter(6, [300, 3400], btype='band', fs=audio.frame_rate)
            filtered_samples = filtfilt(b, a, samples)
        else:  # auto
            # Adaptive filtering based on audio characteristics
            b, a = butter(4, [250, 3800], btype='band', fs=audio.frame_rate)
            filtered_samples = filtfilt(b, a, samples)
        
        # Convert back to original format
        if audio.sample_width == 2:
            filtered_samples = (filtered_samples * 32768.0).astype(np.int16)
        elif audio.sample_width == 4:
            filtered_samples = (filtered_samples * 2147483648.0).astype(np.int32)
        
        # Create new AudioSegment
        filtered_audio = audio._spawn(filtered_samples.tobytes())
        return filtered_audio
        
    except Exception as e:
        logger.warning(f"Noise reduction failed: {e}, returning original audio")
        return audio


def split_audio_by_time(audio, chunk_length_seconds, overlap_seconds=0):
    """
    Split audio into time-based chunks.
    
    Args:
        audio: AudioSegment object
        chunk_length_seconds: Length of each chunk in seconds
        overlap_seconds: Overlap between chunks in seconds
    
    Returns:
        List of AudioSegment chunks
    """
    chunks = []
    chunk_length_ms = chunk_length_seconds * 1000
    overlap_ms = overlap_seconds * 1000
    
    start_time = 0
    while start_time < len(audio):
        end_time = min(start_time + chunk_length_ms, len(audio))
        chunk = audio[start_time:end_time]
        
        # Only add chunks with sufficient duration (at least 1 second)
        if len(chunk) >= 1000:
            chunks.append(chunk)
        
        # Move start time with overlap consideration
        start_time = end_time - overlap_ms
        
        # Avoid infinite loop
        if start_time >= end_time:
            break
    
    return chunks


def recognize_speech_in_chunk(chunk_wav_path, engine, language, quality, time_offset=0):
    """
    Recognize speech in a single audio chunk.
    
    Args:
        chunk_wav_path: Path to WAV file
        engine: Recognition engine ('whisper', 'google', 'sphinx')
        language: Language code
        quality: Quality setting
        time_offset: Time offset for this chunk in seconds
    
    Returns:
        Tuple of (text, segments_list)
    """
    try:
        # Try Whisper first if available
        if engine == 'whisper':
            try:
                return recognize_with_whisper_local(chunk_wav_path, language, time_offset)
            except Exception as e:
                logger.warning(f"Local Whisper failed: {e}, trying Google")
                engine = 'google'  # Fallback to Google
        
        # Use Google Speech Recognition
        if engine == 'google':
            return recognize_with_google_enhanced(chunk_wav_path, language, quality, time_offset)
        
        # Use Sphinx as last resort
        elif engine == 'sphinx':
            return recognize_with_sphinx(chunk_wav_path, language, time_offset)
        
        else:
            # Default to Google
            return recognize_with_google_enhanced(chunk_wav_path, language, quality, time_offset)
    
    except Exception as e:
        logger.error(f"Speech recognition failed for chunk: {e}")
        return '', []


def recognize_with_whisper_local(audio_path, language, time_offset):
    """
    Use local Whisper model for speech recognition.
    """
    try:
        # Try faster-whisper first
        try:
            from faster_whisper import WhisperModel
            
            model = WhisperModel("base", device="cpu", compute_type="int8")
            
            # Map language codes
            lang_map = {
                'ru': 'ru', 'ru-RU': 'ru',
                'en': 'en', 'en-US': 'en',
                'uk': 'uk', 'uk-UA': 'uk',
                'de': 'de', 'de-DE': 'de',
                'fr': 'fr', 'fr-FR': 'fr',
                'es': 'es', 'es-ES': 'es',
                'it': 'it', 'it-IT': 'it',
                'ja': 'ja', 'ja-JP': 'ja',
                'ko': 'ko', 'ko-KR': 'ko',
                'zh': 'zh', 'zh-CN': 'zh'
            }
            whisper_lang = lang_map.get(language, 'ru')
            
            segments, info = model.transcribe(
                audio_path, 
                language=whisper_lang,
                beam_size=5,
                best_of=5,
                temperature=0.0,
                condition_on_previous_text=False
            )
            
            text_parts = []
            segment_list = []
            
            for segment in segments:
                segment_text = segment.text.strip()
                if segment_text:
                    text_parts.append(segment_text)
                    segment_list.append({
                        'start': round(time_offset + segment.start, 2),
                        'end': round(time_offset + segment.end, 2),
                        'text': segment_text
                    })
            
            full_text = ' '.join(text_parts)
            return full_text, segment_list
            
        except ImportError:
            # Try regular whisper
            try:
                import whisper
                
                model = whisper.load_model("base")
                result = model.transcribe(
                    audio_path,
                    language=language if language != 'auto' else None,
                    task="transcribe",
                    verbose=False
                )
                
                full_text = result['text'].strip()
                segments = []
                
                if 'segments' in result:
                    for segment in result['segments']:
                        segments.append({
                            'start': round(time_offset + segment['start'], 2),
                            'end': round(time_offset + segment['end'], 2),
                            'text': segment['text'].strip()
                        })
                
                return full_text, segments
                
            except ImportError:
                raise Exception("Neither faster-whisper nor whisper is available")
    
    except Exception as e:
        logger.error(f"Whisper recognition failed: {e}")
        raise e


def recognize_with_google_enhanced(audio_path, language, quality, time_offset):
    """
    Enhanced Google Speech Recognition with better settings.
    """
    try:
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        
        # Enhanced settings based on quality
        if quality == 'high':
            recognizer.energy_threshold = 200
            recognizer.dynamic_energy_threshold = True
            recognizer.dynamic_energy_adjustment_damping = 0.15
            recognizer.dynamic_energy_ratio = 1.5
            recognizer.pause_threshold = 0.8
            recognizer.operation_timeout = 30
            recognizer.phrase_threshold = 0.3
            recognizer.non_speaking_duration = 0.5
        elif quality == 'fast':
            recognizer.energy_threshold = 4000
            recognizer.pause_threshold = 0.5
            recognizer.phrase_threshold = 0.5
            recognizer.operation_timeout = 10
        else:  # standard
            recognizer.energy_threshold = 300
            recognizer.pause_threshold = 0.8
            recognizer.phrase_threshold = 0.3
            recognizer.operation_timeout = 20
        
        # Map language codes for Google API
        language_mapping = {
            'ru': 'ru-RU',
            'en': 'en-US',
            'uk': 'uk-UA',
            'de': 'de-DE',
            'fr': 'fr-FR',
            'es': 'es-ES',
            'it': 'it-IT',
            'ja': 'ja-JP',
            'ko': 'ko-KR',
            'zh': 'zh-CN'
        }
        
        google_language = language_mapping.get(language, 'ru-RU')
        
        with sr.AudioFile(audio_path) as source:
            # Adjust for ambient noise
            if quality == 'high':
                recognizer.adjust_for_ambient_noise(source, duration=1)
            
            audio_data = recognizer.record(source)
        
        # Try Google recognition with show_all=True for better results
        try:
            # First try with show_all to get confidence scores
            result = recognizer.recognize_google(
                audio_data, 
                language=google_language,
                show_all=True
            )
            
            if result and 'alternative' in result:
                # Get the best result
                best_alternative = result['alternative'][0]
                text = best_alternative['transcript']
                
                # Create a simple segment
                segments = [{
                    'start': round(time_offset, 2),
                    'end': round(time_offset + (len(audio_data.frame_data) / audio_data.sample_rate), 2),
                    'text': text.strip()
                }]
                
                return text.strip(), segments
            else:
                return '', []
        
        except sr.UnknownValueError:
            logger.warning("Google could not understand the audio in this chunk")
            return '', []
        except sr.RequestError as e:
            logger.error(f"Google API error: {e}")
            # Try without show_all as fallback
            try:
                text = recognizer.recognize_google(audio_data, language=google_language)
                segments = [{
                    'start': round(time_offset, 2),
                    'end': round(time_offset + (len(audio_data.frame_data) / audio_data.sample_rate), 2),
                    'text': text.strip()
                }]
                return text.strip(), segments
            except:
                return '', []
    
    except Exception as e:
        logger.error(f"Google recognition failed: {e}")
        return '', []


def recognize_with_sphinx(audio_path, language, time_offset):
    """
    Use CMU Sphinx for offline recognition (limited accuracy).
    """
    try:
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        
        try:
            text = recognizer.recognize_sphinx(audio_data)
            segments = [{
                'start': round(time_offset, 2),
                'end': round(time_offset + (len(audio_data.frame_data) / audio_data.sample_rate), 2),
                'text': text.strip()
            }]
            return text.strip(), segments
        except sr.UnknownValueError:
            return '', []
        except sr.RequestError as e:
            logger.error(f"Sphinx error: {e}")
            return '', []
    
    except Exception as e:
        logger.error(f"Sphinx recognition failed: {e}")
        return '', []


def post_process_text(text, language):
    """
    Post-process recognized text for better readability.
    
    Args:
        text: Raw recognized text
        language: Language code
    
    Returns:
        Processed text
    """
    if not text:
        return text
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    # Add period at the end if missing
    if text and text[-1] not in '.!?':
        text += '.'
    
    # Language-specific post-processing
    if language.startswith('ru'):
        # Russian-specific fixes
        text = text.replace(' не ', ' не ')
        text = text.replace('ё', 'е')  # Normalize yo to ye
    elif language.startswith('en'):
        # English-specific fixes
        text = text.replace(' i ', ' I ')
        text = text.replace(' i\'', ' I\'')
    
    return text

class VideoUploadView(View):
    """
    Dedicated view for handling video uploads and conversion.
    Handles POST requests with VideoUploadForm and saves files to MEDIA_ROOT/tmp.
    """
    
    def get(self, request):
        """Display the upload form."""
        form = VideoUploadForm()
        return render(request, 'converter/home.html', {'form': form})
    
    def post(self, request):
        """Handle video upload and initiate conversion."""
        form = VideoUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Get conversion settings from form
                conversion_settings = form.get_conversion_settings()
                if not conversion_settings:
                    messages.error(request, 'Ошибка валидации настроек конвертации')
                    return render(request, 'converter/home.html', {'form': form})
                
                # Extract uploaded file separately (can't be JSON serialized)
                uploaded_file = conversion_settings.pop('video_file')
                tmp_dir = Path(settings.MEDIA_ROOT) / 'tmp'
                tmp_dir.mkdir(exist_ok=True)
                
                # Generate unique filename
                file_extension = Path(uploaded_file.name).suffix
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                tmp_file_path = tmp_dir / unique_filename
                
                # Save file
                with open(tmp_file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                logger.info(f"Video uploaded to temporary location: {tmp_file_path}")
                
                # Create conversion task
                task = ConversionTask.objects.create(
                    status=ConversionTask.STATUS_QUEUED
                )
                
                # Set task metadata
                task.set_metadata(
                    original_filename=uploaded_file.name,
                    input_path=str(tmp_file_path),
                    file_size=uploaded_file.size,
                    conversion_params=conversion_settings,
                    file_type='video',
                    input_format=file_extension.lstrip('.').lower()
                )
                task.save()
                
                # Initialize conversion service
                conversion_service = VideoConversionService()
                
                # Perform conversion (synchronous for now)
                try:
                    result = conversion_service.convert_video_to_gif(
                        task_id=task.id,
                        input_path=str(tmp_file_path),
                        **conversion_settings
                    )
                    
                    if result['success']:
                        # Return file download response
                        return self._serve_converted_file(result['output_path'])
                    else:
                        # Handle conversion error
                        error_msg = result.get('error_message', 'Неизвестная ошибка конвертации')
                        messages.error(request, f'Ошибка конвертации: {error_msg}')
                        logger.error(f"Conversion failed for task {task.id}: {error_msg}")
                        
                except Exception as e:
                    error_msg = f'Ошибка при обработке видео: {str(e)}'
                    messages.error(request, error_msg)
                    logger.error(f"Conversion exception for task {task.id}: {e}")
                    
                    # Update task status
                    task.fail(str(e))
                
            except Exception as e:
                error_msg = f'Ошибка при загрузке файла: {str(e)}'
                messages.error(request, error_msg)
                logger.error(f"Upload error: {e}")
        
        else:
            # Form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields[field].label}: {error}')
        
        return render(request, 'converter/home.html', {'form': form})
    
    def _serve_converted_file(self, file_path):
        """Serve the converted GIF file for download."""
        if not os.path.exists(file_path):
            raise Http404("Конвертированный файл не найден")
        
        filename = os.path.basename(file_path)
        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=filename,
            content_type='image/gif'
        )
        
        # Add headers for better download experience
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = os.path.getsize(file_path)
        
        return response

def home_view(request):
    """Redirect to the new upload view."""
    upload_view = VideoUploadView.as_view()
    return upload_view(request)

def convert_video_view(request):
    return render(request, 'converter/index.html', {'form': VideoUploadForm()})

def converter_status_view(request):
    return JsonResponse({'status': 'operational', 'version': '1.0.0'})

# Additional placeholder views for navigation links
def photos_to_gif_view(request):
    """View for photos to GIF conversion."""
    return render(request, 'converter/photos_to_gif.html')

def audio_to_text_view(request):
    """View for audio to text conversion."""
    return render(request, 'converter/audio_to_text.html')

def conversion_interface_view(request):
    """View for conversion interface."""
    return render(request, 'converter/conversion_interface.html')

def comprehensive_converter_view(request):
    """View for comprehensive converter."""
    return render(request, 'converter/comprehensive_converter.html')

@require_http_methods(["POST"])
@csrf_exempt
def video_info_view(request):
    """Get video information via AJAX."""
    if not request.FILES.get('video'):
        return JsonResponse({'success': False, 'error': 'No video file provided'})
    
    try:
        video_file = request.FILES['video']
        converter = VideoConverter()
        info = converter.get_video_info(video_file)
        
        if info:
            return JsonResponse({
                'success': True,
                'info': info
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Could not extract video information'
            })
            
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Server error while processing video'
        })

@require_http_methods(["POST"])
@csrf_exempt
def api_photos_to_gif_view(request):
    """API endpoint for converting photos to GIF."""
    try:
        from .utils import PhotoToGifConverter
        import tempfile
        import uuid
        
        # Check if images are provided
        images = request.FILES.getlist('images')
        if not images:
            return JsonResponse({
                'success': False,
                'error': 'No images provided'
            })
        
        # Get parameters from request
        frame_duration = float(request.POST.get('frame_duration', 0.5)) * 1000  # Convert to milliseconds
        output_size = request.POST.get('output_size', '480')
        colors = int(request.POST.get('colors', 128))
        loop = request.POST.get('loop', 'true').lower() == 'true'
        sort_order = request.POST.get('sort_order', 'filename')
        pingpong = request.POST.get('pingpong', 'false').lower() == 'true'
        optimize = request.POST.get('optimize', 'true').lower() == 'true'
        
        # Sort images if needed
        if sort_order == 'filename':
            images = sorted(images, key=lambda x: x.name)
        # Add more sorting options if needed
        
        # Determine output size
        resize = None
        if output_size != 'original' and output_size.isdigit():
            size = int(output_size)
            resize = (size, size)
        
        # Create temporary output file
        temp_dir = Path(settings.MEDIA_ROOT) / 'temp'
        temp_dir.mkdir(exist_ok=True)
        
        output_filename = f"photos_to_gif_{uuid.uuid4().hex[:8]}.gif"
        output_path = temp_dir / output_filename
        
        # Initialize converter
        converter = PhotoToGifConverter()
        
        # Convert photos to GIF
        success = converter.create_gif_from_photos(
            photo_files=images,
            output_path=str(output_path),
            duration=int(frame_duration),
            loop=0 if loop else 1,
            quality=85,
            resize=resize,
            reverse=pingpong,
            optimize=optimize
        )
        
        if success and output_path.exists():
            # Move to final location
            final_dir = Path(settings.MEDIA_ROOT) / 'gifs'
            final_dir.mkdir(exist_ok=True)
            
            final_filename = f"photos_{uuid.uuid4().hex[:8]}.gif"
            final_path = final_dir / final_filename
            
            import shutil
            shutil.move(str(output_path), str(final_path))
            
            # Generate URL
            gif_url = f"{settings.MEDIA_URL}gifs/{final_filename}"
            
            # Get file info
            file_size = final_path.stat().st_size
            total_duration = len(images) * (frame_duration / 1000)
            
            return JsonResponse({
                'success': True,
                'gif_url': gif_url,
                'file_info': {
                    'frames': len(images),
                    'duration_per_frame': frame_duration / 1000,
                    'total_duration': total_duration,
                    'file_size': file_size,
                    'dimensions': f"{resize[0]}x{resize[1]}" if resize else 'Original'
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create GIF from photos'
            })
            
    except Exception as e:
        logger.error(f"Error creating GIF from photos: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })


@require_http_methods(["POST"])
@csrf_exempt
def api_conversion_submit(request):
    """
    API endpoint for submitting conversion tasks.
    """
    try:
        if not request.FILES.get('file'):
            return JsonResponse({
                'success': False,
                'error': 'No file provided'
            })
        
        uploaded_file = request.FILES['file']
        source_format = request.POST.get('source_format')
        target_format = request.POST.get('target_format')
        params_json = request.POST.get('params', '{}')
        
        # Parse additional parameters
        try:
            params = json.loads(params_json)
        except json.JSONDecodeError:
            params = {}
        
        logger.info(f"Conversion request: {source_format} -> {target_format}, file: {uploaded_file.name}")
        
        # Route to appropriate conversion function based on format
        if source_format == 'video' and target_format == 'gif':
            # Use existing video to GIF conversion
            return handle_video_to_gif_conversion(request, uploaded_file, params)
        elif source_format == 'image':
            # Use existing image conversion
            return handle_image_conversion(request, uploaded_file, target_format, params)
        else:
            return JsonResponse({
                'success': False,
                'error': f'Conversion from {source_format} to {target_format} is not supported yet'
            })
            
    except Exception as e:
        logger.error(f"Error in conversion submit: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })


def handle_video_to_gif_conversion(request, video_file, params):
    """Handle video to GIF conversion using existing logic."""
    try:
        # Extract parameters with defaults
        width = params.get('width', 480)
        fps = params.get('fps', 15)
        start_time = params.get('start_time', 0)
        end_time = params.get('end_time')
        quality = params.get('quality', 'medium')
        
        # Create temporary files
        temp_dir = Path(settings.MEDIA_ROOT) / 'temp'
        temp_dir.mkdir(exist_ok=True)
        
        video_filename = f"video_{uuid.uuid4().hex[:8]}{Path(video_file.name).suffix}"
        video_path = temp_dir / video_filename
        
        # Save uploaded video file
        with open(video_path, 'wb+') as destination:
            for chunk in video_file.chunks():
                destination.write(chunk)
        
        # Create output GIF file
        gif_filename = f"video_to_gif_{uuid.uuid4().hex[:8]}.gif"
        gif_path = temp_dir / gif_filename
        
        # Convert video to GIF
        converter = VideoConverter()
        success = converter.convert_to_gif(
            input_path=str(video_path),
            output_path=str(gif_path),
            width=int(width) if width else None,
            fps=int(fps),
            start_time=float(start_time) if start_time else 0,
            end_time=float(end_time) if end_time else None
        )
        
        if success and gif_path.exists():
            # Move to final location
            final_dir = Path(settings.MEDIA_ROOT) / 'gifs'
            final_dir.mkdir(exist_ok=True)
            
            final_gif_filename = f"converted_{uuid.uuid4().hex[:8]}.gif"
            final_gif_path = final_dir / final_gif_filename
            
            import shutil
            shutil.move(str(gif_path), str(final_gif_path))
            
            # Clean up temporary video file
            try:
                video_path.unlink()
            except:
                pass
            
            # Generate URL
            gif_url = f"{settings.MEDIA_URL}gifs/{final_gif_filename}"
            
            return JsonResponse({
                'success': True,
                'task_id': uuid.uuid4().hex,
                'output_url': gif_url,
                'file_size': final_gif_path.stat().st_size
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to convert video to GIF'
            })
            
    except Exception as e:
        logger.error(f"Error in video to GIF conversion: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Video conversion error: {str(e)}'
        })


def handle_image_conversion(request, image_file, target_format, params):
    """Handle image conversion using existing logic."""
    try:
        # Extract parameters
        quality = int(params.get('quality', 85))
        width = params.get('width')
        height = params.get('height')
        
        # Create temporary files
        temp_dir = Path(settings.MEDIA_ROOT) / 'temp'
        temp_dir.mkdir(exist_ok=True)
        
        input_filename = f"input_{uuid.uuid4().hex[:8]}{Path(image_file.name).suffix}"
        input_path = temp_dir / input_filename
        
        # Save uploaded file
        with open(input_path, 'wb+') as destination:
            for chunk in image_file.chunks():
                destination.write(chunk)
        
        # Create output file
        output_filename = f"converted_{uuid.uuid4().hex[:8]}.{target_format}"
        output_path = temp_dir / output_filename
        
        try:
            from PIL import Image
            
            # Open and process image
            with Image.open(input_path) as img:
                # Resize if specified
                if width or height:
                    new_width = int(width) if width else img.width
                    new_height = int(height) if height else img.height
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save with appropriate settings
                save_kwargs = {'format': target_format.upper()}
                if target_format.lower() in ['jpg', 'jpeg']:
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                    # Convert to RGB if has alpha channel
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                
                img.save(output_path, **save_kwargs)
            
            # Move to final location
            final_dir = Path(settings.MEDIA_ROOT) / 'images'
            final_dir.mkdir(exist_ok=True)
            
            final_filename = f"converted_{uuid.uuid4().hex[:8]}.{target_format}"
            final_path = final_dir / final_filename
            
            import shutil
            shutil.move(str(output_path), str(final_path))
            
            # Clean up input file
            try:
                input_path.unlink()
            except:
                pass
            
            # Generate URL
            output_url = f"{settings.MEDIA_URL}images/{final_filename}"
            
            return JsonResponse({
                'success': True,
                'task_id': uuid.uuid4().hex,
                'output_url': output_url,
                'file_size': final_path.stat().st_size
            })
            
        except ImportError:
            return JsonResponse({
                'success': False,
                'error': 'PIL library not available'
            })
            
    except Exception as e:
        logger.error(f"Error in image conversion: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Image conversion error: {str(e)}'
        })


@require_http_methods(["GET"])
def api_conversion_queue(request):
    """
    API endpoint for getting conversion queue status.
    Since we don't have a persistent queue system, return mock data.
    """
    try:
        # Mock queue data - in a real system this would come from a database
        tasks = [
            {
                'id': 1,
                'filename': 'example.mp4',
                'source_format': 'video',
                'target_format': 'gif',
                'status': 'done',
                'progress': 100,
                'created_at': '2024-01-01T12:00:00Z',
                'error_message': None
            },
            {
                'id': 2,
                'filename': 'image.jpg',
                'source_format': 'image',
                'target_format': 'png',
                'status': 'running',
                'progress': 75,
                'created_at': '2024-01-01T12:05:00Z',
                'error_message': None
            }
        ]
        
        return JsonResponse({
            'success': True,
            'tasks': tasks,
            'total': len(tasks)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversion queue: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })


@require_http_methods(["POST"])
@csrf_exempt
def ajax_convert_video(request):
    """
    AJAX endpoint для конвертации видео в GIF.
    """
    try:
        if not request.FILES.get('video'):
            return JsonResponse({
                'success': False,
                'error': 'Video file not provided'
            })
        
        video_file = request.FILES['video']
        
        # Получаем параметры конвертации
        width = request.POST.get('width')
        fps = int(request.POST.get('fps', 15))
        start_time = float(request.POST.get('start_time', 0))
        end_time = request.POST.get('end_time')
        grayscale = request.POST.get('grayscale') == '1'
        reverse = request.POST.get('reverse') == '1'
        boomerang = request.POST.get('boomerang') == '1'
        
        end_time = float(end_time) if end_time else None
        
        # Создаём временный файл для загруженного видео
        temp_dir = Path(settings.MEDIA_ROOT) / 'temp'
        temp_dir.mkdir(exist_ok=True)
        
        video_filename = f"video_{uuid.uuid4().hex[:8]}{Path(video_file.name).suffix}"
        video_path = temp_dir / video_filename
        
        # Сохраняем загруженный видео файл
        with open(video_path, 'wb+') as destination:
            for chunk in video_file.chunks():
                destination.write(chunk)
        
        # Создаём выходной GIF файл
        gif_filename = f"video_to_gif_{uuid.uuid4().hex[:8]}.gif"
        gif_path = temp_dir / gif_filename
        
        # Конвертируем видео в GIF
        converter = VideoConverter()
        success = converter.convert_to_gif(
            input_path=str(video_path),
            output_path=str(gif_path),
            width=int(width) if width else None,
            fps=fps,
            start_time=start_time,
            end_time=end_time,
            grayscale=grayscale,
            reverse=reverse,
            boomerang=boomerang
        )
        
        if success and gif_path.exists():
            # Перемещаем в финальную директорию
            final_dir = Path(settings.MEDIA_ROOT) / 'gifs'
            final_dir.mkdir(exist_ok=True)
            
            final_gif_filename = f"converted_{uuid.uuid4().hex[:8]}.gif"
            final_gif_path = final_dir / final_gif_filename
            
            import shutil
            shutil.move(str(gif_path), str(final_gif_path))
            
            # Удаляем временный видео файл
            try:
                video_path.unlink()
            except:
                pass
            
            # Генерируем URL
            gif_url = f"{settings.MEDIA_URL}gifs/{final_gif_filename}"
            
            # Получаем информацию о файле
            file_size = final_gif_path.stat().st_size
            
            return JsonResponse({
                'success': True,
                'gif_url': gif_url,
                'file_size': file_size
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to convert video to GIF'
            })
    
    except Exception as e:
        logger.error(f"Error in AJAX video conversion: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })


@require_http_methods(["POST"])
@csrf_exempt
def convert_with_adapters(request):
    """
    API endpoint для конвертации изображений с использованием адаптеров.
    """
    try:
        if not request.FILES.get('file'):
            return JsonResponse({
                'success': False,
                'error': 'File not provided'
            })
        
        uploaded_file = request.FILES['file']
        output_format = request.POST.get('output_format', 'jpg')
        
        # Получаем параметры
        width = request.POST.get('width')
        height = request.POST.get('height')
        quality = int(request.POST.get('quality', 90))
        
        # Параметры для анимированного GIF
        create_animated_gif = request.POST.get('create_animated_gif') == '1'
        gif_effect = request.POST.get('gif_effect', 'fade')
        gif_duration = int(request.POST.get('gif_duration', 200))
        gif_frames = int(request.POST.get('gif_frames', 10))
        gif_loop = request.POST.get('gif_loop') == '1'
        
        # Создаём временные файлы
        temp_dir = Path(settings.MEDIA_ROOT) / 'temp'
        temp_dir.mkdir(exist_ok=True)
        
        input_filename = f"input_{uuid.uuid4().hex[:8]}{Path(uploaded_file.name).suffix}"
        input_path = temp_dir / input_filename
        
        # Сохраняем загруженный файл
        with open(input_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Создаём выходной файл
        output_filename = f"converted_{uuid.uuid4().hex[:8]}.{output_format}"
        output_path = temp_dir / output_filename
        
        try:
            from PIL import Image
            
            # Открываем изображение
            with Image.open(input_path) as img:
                # Изменяем размер если нужно
                if width or height:
                    new_width = int(width) if width else img.width
                    new_height = int(height) if height else img.height
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Если нужно создать анимированный GIF
                if create_animated_gif and output_format.lower() == 'gif':
                    # Создаём простую анимацию
                    frames = []
                    for i in range(gif_frames):
                        frame = img.copy()
                        # Применяем простые эффекты
                        if gif_effect == 'fade':
                            alpha = int(255 * (0.3 + 0.7 * abs(i - gif_frames//2) / (gif_frames//2)))
                            frame.putalpha(alpha)
                        frames.append(frame)
                    
                    # Сохраняем как анимированный GIF
                    frames[0].save(
                        output_path,
                        format='GIF',
                        save_all=True,
                        append_images=frames[1:],
                        duration=gif_duration,
                        loop=0 if gif_loop else 1,
                        optimize=True
                    )
                else:
                    # Обычное сохранение
                    save_kwargs = {'format': output_format.upper()}
                    if output_format.lower() == 'jpeg':
                        save_kwargs['quality'] = quality
                        save_kwargs['optimize'] = True
                        # Конвертируем в RGB если есть альфа-канал
                        if img.mode in ('RGBA', 'LA', 'P'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = background
                    
                    img.save(output_path, **save_kwargs)
            
            if output_path.exists():
                # Перемещаем в финальную директорию
                final_dir = Path(settings.MEDIA_ROOT) / 'images'
                final_dir.mkdir(exist_ok=True)
                
                final_filename = f"converted_{uuid.uuid4().hex[:8]}.{output_format}"
                final_path = final_dir / final_filename
                
                import shutil
                shutil.move(str(output_path), str(final_path))
                
                # Удаляем временный входной файл
                try:
                    input_path.unlink()
                except:
                    pass
                
                # Генерируем URL
                output_url = f"{settings.MEDIA_URL}images/{final_filename}"
                
                return JsonResponse({
                    'success': True,
                    'output_url': output_url,
                    'output_path': str(final_path),
                    'file_size': final_path.stat().st_size
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to process image'
                })
        
        except ImportError:
            return JsonResponse({
                'success': False,
                'error': 'PIL library not available'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Image processing error: {str(e)}'
            })
    
    except Exception as e:
        logger.error(f"Error in image conversion: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })


@require_http_methods(["GET"])
def engine_status(request):
    """
    API endpoint для получения статуса движков конвертации.
    """
    try:
        status = {
            'video': {
                'available': True,
                'supported_formats': {
                    'input': ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'],
                    'output': ['gif']
                }
            },
            'image': {
                'available': True,
                'supported_formats': {
                    'input': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
                    'output': ['jpg', 'jpeg', 'png', 'gif', 'webp']
                }
            },
            'audio': {
                'available': False,  # Пока не реализовано
                'supported_formats': {
                    'input': [],
                    'output': []
                }
            },
            'document': {
                'available': False,  # Пока не реализовано
                'supported_formats': {
                    'input': [],
                    'output': []
                }
            },
            'archive': {
                'available': False,  # Пока не реализовано
                'supported_formats': {
                    'input': [],
                    'output': []
                }
            }
        }
        
        # Проверяем доступность ffmpeg для видео
        try:
            converter = VideoConverter()
            if hasattr(converter, 'ffmpeg_path'):
                status['video']['available'] = True
            else:
                status['video']['available'] = False
        except:
            status['video']['available'] = False
        
        # Проверяем доступность PIL для изображений
        try:
            from PIL import Image
            status['image']['available'] = True
        except ImportError:
            status['image']['available'] = False
        
        return JsonResponse(status)
    
    except Exception as e:
        logger.error(f"Error getting engine status: {str(e)}")
        return JsonResponse({
            'error': f'Server error: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def api_audio_to_text_view(request):
    """
    Enhanced API endpoint for audio to text conversion using advanced speech recognition.
    Supports chunking, multiple engines, and better accuracy.
    """
    try:
        # Check if audio file is provided
        if not request.FILES.get('audio'):
            return JsonResponse({
                'success': False,
                'error': 'No audio file provided'
            })
        
        audio_file = request.FILES['audio']
        
        # Get parameters from request
        engine = request.POST.get('engine', 'whisper')  # Изменено с 'google' на 'whisper'
        language = request.POST.get('language', 'ru')
        quality = request.POST.get('quality', 'high')  # Изменено с 'standard' на 'high'
        output_format = request.POST.get('output_format', 'text')
        include_timestamps = request.POST.get('include_timestamps', 'true').lower() == 'true'  # По умолчанию включено
        detect_speakers = request.POST.get('detect_speakers', 'false').lower() == 'true'
        chunk_length = int(request.POST.get('chunk_length', '30'))  # Длина чанка в секундах
        overlap = int(request.POST.get('overlap', '2'))  # Перекрытие между чанками
        
        # Advanced audio settings
        volume_gain = request.POST.get('volume_gain', '100')
        noise_reduction = request.POST.get('noise_reduction', 'auto')  # auto, none, light, medium, strong
        enable_normalization = request.POST.get('enable_normalization', 'true').lower() == 'true'
        enhance_speech = request.POST.get('enhance_speech', 'true').lower() == 'true'
        remove_silence = request.POST.get('remove_silence', 'true').lower() == 'true'
        
        # Validate audio file
        max_size = 100 * 1024 * 1024  # 100 MB
        if audio_file.size > max_size:
            return JsonResponse({
                'success': False,
                'error': 'File too large. Maximum size is 100 MB.'
            })
        
        # Check file format
        allowed_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma', '.opus', '.mp4', '.avi', '.mov']
        file_extension = Path(audio_file.name).suffix.lower()
        if file_extension not in allowed_extensions:
            return JsonResponse({
                'success': False,
                'error': f'Unsupported file format. Allowed formats: {", ".join(allowed_extensions)}'
            })
        
        logger.info(f"Processing enhanced audio-to-text: file={audio_file.name}, engine={engine}, language={language}, chunks={chunk_length}s")
        
        # Import required libraries
        try:
            import speech_recognition as sr
            from pydub import AudioSegment
            from pydub.silence import split_on_silence
            from pydub.effects import normalize
            import numpy as np
        except ImportError as e:
            logger.error(f"Required libraries not available: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Speech recognition libraries not available. Please install speech_recognition, pydub, and numpy.'
            })
        
        # Create temporary file for processing
        import tempfile
        import time
        import math
        
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            # Write uploaded file to temporary file
            for chunk in audio_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Load and preprocess audio with pydub
            logger.info("Loading and preprocessing audio...")
            audio = AudioSegment.from_file(temp_file_path)
            
            # Get original duration
            original_duration = len(audio) / 1000.0
            logger.info(f"Original audio duration: {original_duration:.2f} seconds")
            
            # Convert to optimal format for speech recognition
            audio = audio.set_channels(1)  # Mono
            audio = audio.set_frame_rate(16000)  # 16kHz sample rate
            
            # Apply volume gain if requested
            if float(volume_gain) != 100:
                gain_db = 20 * math.log10(float(volume_gain) / 100)
                audio = audio + gain_db
                logger.info(f"Applied volume gain: {gain_db:.1f}dB")
            
            # Normalize audio for better recognition
            if enable_normalization:
                audio = normalize(audio)
                logger.info("Applied audio normalization")
            
            # Enhanced speech processing
            if enhance_speech:
                # Apply high-pass filter to remove low-frequency noise
                audio = audio.high_pass_filter(300)
                # Apply low-pass filter to remove high-frequency noise
                audio = audio.low_pass_filter(3400)
                logger.info("Applied speech enhancement filters")
            
            # Advanced noise reduction using spectral subtraction (if numpy available)
            if noise_reduction != 'none' and 'numpy' in locals():
                try:
                    audio = apply_noise_reduction(audio, noise_reduction)
                    logger.info(f"Applied {noise_reduction} noise reduction")
                except Exception as e:
                    logger.warning(f"Noise reduction failed: {e}")
            
            # Split audio into chunks for better processing
            chunks = []
            
            if remove_silence and len(audio) > 30000:  # Only for audio longer than 30 seconds
                logger.info("Splitting audio by silence...")
                try:
                    # Split on silence
                    silence_chunks = split_on_silence(
                        audio,
                        min_silence_len=1000,  # 1 second of silence
                        silence_thresh=audio.dBFS - 16,  # Silence threshold
                        keep_silence=500,  # Keep 500ms of silence
                        seek_step=100
                    )
                    
                    if len(silence_chunks) > 1:
                        # Merge small chunks and split large ones
                        processed_chunks = []
                        current_chunk = AudioSegment.empty()
                        
                        for chunk in silence_chunks:
                            # If chunk is too long, split it further
                            if len(chunk) > chunk_length * 1000:
                                if len(current_chunk) > 0:
                                    processed_chunks.append(current_chunk)
                                    current_chunk = AudioSegment.empty()
                                
                                # Split long chunk into smaller pieces
                                chunk_start = 0
                                while chunk_start < len(chunk):
                                    chunk_end = min(chunk_start + chunk_length * 1000, len(chunk))
                                    processed_chunks.append(chunk[chunk_start:chunk_end])
                                    chunk_start = chunk_end - overlap * 1000  # With overlap
                            else:
                                # Add to current chunk if it won't make it too long
                                if len(current_chunk) + len(chunk) <= chunk_length * 1000:
                                    current_chunk += chunk
                                else:
                                    if len(current_chunk) > 0:
                                        processed_chunks.append(current_chunk)
                                    current_chunk = chunk
                        
                        # Add the last chunk
                        if len(current_chunk) > 0:
                            processed_chunks.append(current_chunk)
                        
                        chunks = processed_chunks
                        logger.info(f"Split into {len(chunks)} silence-based chunks")
                    else:
                        # Fallback to time-based chunking
                        chunks = split_audio_by_time(audio, chunk_length, overlap)
                        logger.info(f"Split into {len(chunks)} time-based chunks (silence detection failed)")
                except Exception as e:
                    logger.warning(f"Silence-based splitting failed: {e}, using time-based splitting")
                    chunks = split_audio_by_time(audio, chunk_length, overlap)
            else:
                # Use time-based chunking for shorter audio or when silence detection is disabled
                chunks = split_audio_by_time(audio, chunk_length, overlap)
                logger.info(f"Split into {len(chunks)} time-based chunks")
            
            # If no chunks were created, use the whole audio
            if not chunks:
                chunks = [audio]
            
            # Process each chunk
            all_segments = []
            total_chunks = len(chunks)
            current_time_offset = 0
            
            logger.info(f"Processing {total_chunks} audio chunks...")
            
            for i, chunk in enumerate(chunks):
                chunk_duration = len(chunk) / 1000.0
                logger.info(f"Processing chunk {i+1}/{total_chunks} (duration: {chunk_duration:.2f}s)")
                
                try:
                    # Convert chunk to WAV for speech recognition
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as chunk_file:
                        chunk.export(chunk_file.name, format="wav")
                        chunk_wav_path = chunk_file.name
                    
                    # Recognize speech in this chunk
                    chunk_text, chunk_segments = recognize_speech_in_chunk(
                        chunk_wav_path, engine, language, quality, current_time_offset
                    )
                    
                    if chunk_text.strip():
                        if chunk_segments:
                            all_segments.extend(chunk_segments)
                        else:
                            # Create a simple segment if no detailed segments
                            all_segments.append({
                                'start': round(current_time_offset, 2),
                                'end': round(current_time_offset + chunk_duration, 2),
                                'text': chunk_text.strip()
                            })
                    
                    current_time_offset += chunk_duration
                    
                    # Clean up chunk file
                    try:
                        os.unlink(chunk_wav_path)
                    except:
                        pass
                
                except Exception as e:
                    logger.error(f"Error processing chunk {i+1}: {e}")
                    # Continue with next chunk
                    current_time_offset += chunk_duration
                    continue
            
            # Combine all text
            full_text = ' '.join([segment['text'] for segment in all_segments if segment['text'].strip()])
            
            # Post-process text
            full_text = post_process_text(full_text, language)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Build response
            response_data = {
                'success': True,
                'text': full_text,
                'metadata': {
                    'engine': engine,
                    'language': language,
                    'quality': quality,
                    'duration': round(original_duration, 2),
                    'file_size': audio_file.size,
                    'file_name': audio_file.name,
                    'processing_time': round(processing_time, 2),
                    'chunks_processed': total_chunks,
                    'segments_found': len(all_segments),
                    'text_length': len(full_text),
                    'words_count': len(full_text.split())
                }
            }
            
            # Add segments if requested
            if include_timestamps and all_segments:
                response_data['segments'] = all_segments
            
            # Add processing details
            response_data['processing_details'] = {
                'chunk_length': chunk_length,
                'overlap': overlap,
                'normalization': enable_normalization,
                'speech_enhancement': enhance_speech,
                'noise_reduction': noise_reduction,
                'silence_detection': remove_silence
            }
            
            logger.info(f"Speech recognition completed successfully: {len(full_text)} characters, {len(all_segments)} segments")
            return JsonResponse(response_data)
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Error in enhanced audio-to-text API: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })
