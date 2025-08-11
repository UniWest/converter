# Hardened Video Upload & Conversion Backend

This document describes the implementation of the hardened video upload and conversion backend system that handles POST requests with VideoUploadForm, processes video files, and converts them to GIF format using FFmpeg.

## System Overview

The hardened backend consists of several key components:

1. **Dedicated Upload View** (`VideoUploadView`) - Handles file uploads and form validation
2. **Conversion Service** (`VideoConversionService`) - Core conversion logic with FFmpeg backend
3. **Task Management** (`ConversionTask` model) - Tracks conversion progress and status
4. **Form Validation** (`VideoUploadForm`) - Comprehensive input validation
5. **Error Handling** - Robust error handling and validation propagation

## Features

### 🔒 Security & Validation

- **File Type Validation**: Only accepts valid video formats
- **File Size Limits**: Configurable maximum upload sizes (500MB default)
- **Time Range Validation**: Ensures start/end times are within video duration
- **Codec Validation**: Checks for supported video codecs using FFprobe
- **Path Sanitization**: Secure file handling with unique filenames

### ⚡ Advanced Conversion Options

- **Resolution Control**: `keep_original_size` toggle or custom width scaling
- **Frame Rate**: Configurable FPS (5-60)
- **Time Trimming**: Start/end time selection with validation
- **Speed Adjustment**: `setpts` filter for speed changes (0.5x-2x)
- **Visual Effects**: 
  - Grayscale conversion
  - Reverse playback
  - Boomerang effect (forward + backward)
- **Quality Options**: High-quality palette generation with configurable dithering

### 🎨 Color & Quality

- **Two-Pass Palette Generation**: For high-quality GIFs
- **Dithering Algorithms**: Bayer, Sierra 2-4A, Floyd-Steinberg, or None
- **Optimized Scaling**: Lanczos filtering for better quality
- **Format Control**: RGB24/Grayscale format handling

## Architecture

### File Flow

```
1. Upload → MEDIA_ROOT/tmp/[uuid].ext
2. Validation → FFprobe metadata check
3. Conversion → FFmpeg processing 
4. Output → MEDIA_ROOT/converted/[uuid].gif
5. Delivery → HTTP file response or download link
```

### Conversion Pipeline

```
Input Video → Validation → Task Creation → Service Processing → Output GIF
     ↓            ↓            ↓              ↓                ↓
   Form       Metadata     Database     FFmpeg/MoviePy    File Response
Validation    Check       Tracking      Processing        Download
```

## Implementation Details

### 1. VideoUploadView

Located in `converter/views.py`, this class-based view handles:

- **GET**: Display upload form
- **POST**: Process file upload and initiate conversion

Key features:
- Form validation with error propagation via Django messages
- Secure file saving to temporary directory
- Task creation and metadata tracking
- Synchronous conversion with progress tracking
- File download response generation

### 2. VideoConversionService  

Located in `converter/services.py`, this service provides:

- **FFmpeg Integration**: Direct subprocess calls with timeout protection
- **Complex Effects**: Falls back to MoviePy for reverse/boomerang effects
- **Progress Tracking**: Real-time progress updates to database
- **Error Handling**: Comprehensive error catching and task failure management
- **File Management**: Automatic cleanup of temporary files

#### FFmpeg Command Structure

```bash
# Basic conversion
ffmpeg -i input.mp4 -ss start -t duration -vf "setpts=PTS/speed,fps=15,scale=width:-1:flags=lanczos,format=rgb24" output.gif

# High-quality two-pass
# Pass 1: Generate palette
ffmpeg -i input.mp4 -vf "filters,palettegen=max_colors=256" palette.png
# Pass 2: Apply palette with dithering  
ffmpeg -i input.mp4 -i palette.png -lavfi "filters[x];[x][1:v]paletteuse=dither=floyd_steinberg" output.gif
```

### 3. Form Validation

The `VideoUploadForm` in `forms.py` provides comprehensive validation:

- **File Validation**: Type, size, and format checking
- **Parameter Validation**: Width, FPS, time ranges
- **Cross-Field Validation**: Time range consistency
- **Settings Export**: Structured data for conversion service

### 4. Error Handling & Messages

The system provides detailed error handling:

- **Upload Errors**: File system, permission, space issues
- **Validation Errors**: Form field validation with specific messages
- **Conversion Errors**: FFmpeg failures, codec issues, timeout errors
- **Task Errors**: Database failures, metadata corruption

Error messages are propagated through:
- Django messages framework (user-facing)
- Task status updates (database)
- Structured logging (debugging)

## Configuration

### Settings Variables

```python
# settings.py
FFMPEG_BINARY = '/path/to/ffmpeg'  # FFmpeg executable path
VIDEO_PROCESSING_TIMEOUT = 300     # 5 minutes conversion timeout
MEDIA_ROOT = '/path/to/media'      # File storage location
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB max upload
```

### Directory Structure

```
MEDIA_ROOT/
├── tmp/           # Uploaded files (temporary)
├── converted/     # Output GIF files
└── ...
```

## Usage Examples

### Basic Conversion

```python
# Form data
form_data = {
    'width': 480,
    'fps': 15,
    'start_time': 10,
    'end_time': 30,
    'keep_original_size': False,
    'speed': '1.0',
    'grayscale': False,
}

# Service call
service = VideoConversionService()
result = service.convert_video_to_gif(
    task_id=task.id,
    input_path='/tmp/video.mp4',
    **form_data
)
```

### High-Quality Conversion

```python
form_data = {
    'width': 720,
    'fps': 24, 
    'high_quality': True,
    'dither': 'floyd_steinberg',
    'grayscale': True,
}
```

### Complex Effects

```python
form_data = {
    'width': 400,
    'fps': 20,
    'speed': '1.5',
    'boomerang': True,  # Forward + reverse
    'high_quality': True,
}
```

## Error Codes & Messages

| Code | Message | Description |
|------|---------|-------------|
| `file_not_found` | "Входной файл не найден" | Upload file missing |
| `ffmpeg_unavailable` | "FFmpeg не найден или недоступен" | FFmpeg binary issue |
| `invalid_format` | "Неподдерживаемый формат видео" | Codec/format not supported |
| `time_range_invalid` | "Время окончания превышает длительность видео" | Invalid time selection |
| `conversion_failed` | "Ошибка при создании GIF файла" | FFmpeg processing error |

## Testing

Run the test suite:

```bash
python test_hardened_conversion.py
```

Test coverage includes:
- Form validation (file types, parameters, time ranges)
- Service functionality (basic, high-quality, effects)
- Error handling (missing files, invalid data)
- View integration (GET/POST handling)

## Celery Integration

For asynchronous processing, use the Celery task:

```python
from converter.tasks import convert_video_to_gif_hardened

# Queue conversion task
result = convert_video_to_gif_hardened.delay(
    task_id=task.id,
    input_path=file_path,
    **conversion_options
)
```

## Performance Considerations

### Optimization Tips

1. **Preprocessing**: Use lower resolution for faster conversion
2. **Time Limits**: Set reasonable start/end times to avoid long processing
3. **Quality Trade-offs**: Single-pass conversion is faster than two-pass
4. **Frame Rate**: Lower FPS significantly reduces processing time
5. **File Cleanup**: Automatic cleanup prevents disk space issues

### Resource Usage

- **CPU**: FFmpeg is CPU-intensive, consider worker limits
- **Memory**: Large videos require substantial RAM for processing  
- **Disk**: Temporary files can accumulate, cleanup is essential
- **Time**: Complex effects can take several minutes to process

## Security Considerations

1. **File Validation**: Strict type and size checking prevents abuse
2. **Path Sanitization**: UUID filenames prevent directory traversal
3. **Resource Limits**: Timeout and size limits prevent DoS
4. **Error Disclosure**: Generic error messages avoid information leakage
5. **Temporary Files**: Automatic cleanup prevents disk filling

## Future Enhancements

- **Progress WebSockets**: Real-time progress updates to frontend
- **Batch Processing**: Multiple file conversion support
- **Preview Generation**: Thumbnail creation before conversion
- **Format Support**: Additional output formats (WebP, APNG)
- **Cloud Storage**: S3/CDN integration for scalability
- **Queue Management**: Priority queuing and load balancing
