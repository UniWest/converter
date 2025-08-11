# 🎬 Media File Converter

A full-featured Django web application for media file conversion with advanced Speech-to-Text (STT) capabilities, video processing, and image manipulation.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Django](https://img.shields.io/badge/Django-5.2.5-green)
![Celery](https://img.shields.io/badge/Celery-5.4.0-green)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-red)
![License](https://img.shields.io/badge/License-Apache--2.0-yellow)

## 🚀 Features

### 📝 Speech-to-Text (STT)
- **Two transcription engines:**
  - 🔥 **faster-whisper** - local processing, high quality
  - 🌐 **Google Speech Recognition** - online API, fast processing for short files
- **Audio preprocessing:**
  - Volume normalization
  - Frequency filtering (HP/LP filters)
  - Noise reduction using noisereduce
  - Silence-based segmentation
- **Supported formats:** MP3, WAV, M4A, FLAC, OGG, AAC, WMA
- **Output formats:** TXT, SRT (subtitles), JSON
- **Languages:** Russian, English, Spanish, French, German, and more

### 🎦 Video to GIF
- Convert videos to animated GIFs
- Customizable quality and size
- Effects: reverse, boomerang, monochrome

### 🖼️ Images to GIF
- Create animations from image sets
- Customizable frame duration
- Ping-pong effects and optimization

### ⚙️ Technical Features
- **Asynchronous tasks:** Celery + Redis
- **Monitoring:** Flower for task tracking
- **Docker:** Full containerization for deployment
- **Portability:** No additional installations required

## 🔧 Setup

### Prerequisites
- **Python:** 3.11+ (recommended)
- **FFmpeg:** Required for audio/video processing
- **Redis:** Required for Celery task queue
- **Git:** For cloning the repository

### Local Installation

1. **Clone the repository:**
```bash
git clone https://github.com/UniWest/converter.git
cd converter
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Setup environment variables:**
```bash
cp .env.example .env
# Edit .env file with your settings
```

5. **Setup database:**
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

6. **Start Redis (required for Celery):**
```bash
# Linux/Mac with Homebrew:
brew services start redis
# or
redis-server

# Ubuntu/Debian:
sudo systemctl start redis-server

# Windows: Install and start Redis
```

7. **Start Celery worker (in separate terminal):**
```bash
source venv/bin/activate  # if not already activated
celery -A converter_site worker --loglevel=info
```

8. **Start Django server:**
```bash
python manage.py runserver
```

9. **Access the application:** http://localhost:8000

### Docker Installation (Recommended)

1. **Clone and setup:**
```bash
git clone https://github.com/UniWest/converter.git
cd converter
cp .env.example .env
```

2. **Build and run with Docker Compose:**
```bash
docker-compose up --build
```

3. **Access the application:** http://localhost:8000
4. **Monitor tasks (optional):** http://localhost:5555 (Flower)

## 🌍 Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

### Core Django Settings
```env
SECRET_KEY=your-secret-key-here
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
```

### Database Configuration
```env
DATABASE_URL=sqlite:///db.sqlite3  # Default SQLite
# For PostgreSQL: DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### Redis & Celery Settings
```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Speech-to-Text Configuration
```env
STT_ENGINE=whisper  # Options: whisper, google
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large-v2, large-v3
WHISPER_DEVICE=auto  # Options: auto, cpu, cuda
WHISPER_COMPUTE_TYPE=int8  # Options: float16, int8, int8_float16
```

### File Processing Limits
```env
FFMPEG_BINARY=ffmpeg  # Path to ffmpeg executable
MEDIA_MAX_SIZE=500  # Maximum file size in MB
AUDIO_MAX_DURATION=3600  # Maximum audio duration in seconds
```

### Security Settings (Production)
```env
SECURE_SSL_REDIRECT=True  # Enable HTTPS redirect
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS=DENY
```

### Logging
```env
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 🧪 Running Tests

### Run All Tests
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# Run tests with pytest
python -m pytest

# Run with coverage
python -m pytest --cov=converter --cov-report=html

# Run specific test categories
python -m pytest -m unit  # Unit tests only
python -m pytest -m integration  # Integration tests only
```

### Run Django Tests
```bash
python manage.py test

# Run specific test modules
python manage.py test converter.tests
```

### Test Categories
- **Unit tests** (`-m unit`): Form validation, utility functions
- **Integration tests** (`-m integration`): Full workflow tests, API endpoints
- **Slow tests** (`-m slow`): Performance and load tests

### Test Files Structure
```
tests/
├── test_form_validation.py      # Form validation tests
├── test_integration_mp4_to_gif.py # Video conversion tests
├── test_stt_functionality.py    # Speech-to-text tests
├── test_ui_functionality.py     # UI interaction tests
└── ...
```

## ⚡ Known Limitations

### Performance Limitations
- **Large files:** Processing files >500MB may timeout or consume excessive memory
- **Whisper models:** Larger models (large-v2, large-v3) require significant RAM (8GB+ recommended)
- **Concurrent processing:** Limited by Redis/Celery configuration and available CPU cores

### Format Limitations
- **Audio formats:** Some exotic formats may require additional FFmpeg codecs
- **Video formats:** H.264/H.265 recommended for best compatibility
- **Image formats:** Animated formats (APNG, WebP) may have limited support

### System Limitations
- **FFmpeg dependency:** Must be installed and accessible in system PATH
- **GPU acceleration:** CUDA support requires NVIDIA drivers and proper configuration
- **Memory usage:** STT processing can consume 2-8GB RAM depending on model size

### API Limitations
- **Google STT:** Requires internet connection and may have quota limits
- **File upload:** Limited by `MEDIA_MAX_SIZE` environment variable
- **Concurrent users:** Performance degrades with high concurrent usage

### Docker Limitations
- **GPU support:** Requires nvidia-docker for CUDA acceleration
- **Volume mounting:** File permissions may require adjustment on some systems
- **Resource allocation:** Container limits may affect processing performance

## 📊 System Requirements

### Minimum Requirements
- **CPU:** 2 cores, 2.0GHz
- **RAM:** 4GB (8GB+ recommended for Whisper)
- **Storage:** 2GB free space (more for media files)
- **OS:** Linux, macOS, Windows 10+

### Recommended Requirements
- **CPU:** 4+ cores, 3.0GHz+
- **RAM:** 16GB+ (for large Whisper models)
- **Storage:** SSD with 10GB+ free space
- **GPU:** NVIDIA GPU with 4GB+ VRAM (for CUDA acceleration)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**UniWest**
- GitHub: [@UniWest](https://github.com/UniWest)

---

⭐ **Star this repository if it was helpful!** ⭐
