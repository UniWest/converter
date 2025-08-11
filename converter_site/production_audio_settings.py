# Production settings for enhanced audio-to-text processing

import os
from pathlib import Path

# Whisper model settings for production
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')  # base, small, medium, large
WHISPER_DEVICE = os.getenv('WHISPER_DEVICE', 'cpu')  # cpu or cuda (if GPU available)
WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')  # int8, int16, float16, float32

# Audio processing limits for production
AUDIO_MAX_DURATION = int(os.getenv('AUDIO_MAX_DURATION', '3600'))  # 1 hour max
AUDIO_MAX_FILE_SIZE = int(os.getenv('AUDIO_MAX_FILE_SIZE', '100'))  # 100 MB max
AUDIO_CHUNK_LENGTH = int(os.getenv('AUDIO_CHUNK_LENGTH', '30'))  # 30 seconds default

# Performance settings
AUDIO_PROCESSING_TIMEOUT = int(os.getenv('AUDIO_PROCESSING_TIMEOUT', '1800'))  # 30 minutes
CONCURRENT_AUDIO_JOBS = int(os.getenv('CONCURRENT_AUDIO_JOBS', '2'))  # Limit concurrent processing

# Cache directory for models
WHISPER_CACHE_DIR = os.getenv('WHISPER_CACHE_DIR', Path.home() / '.cache' / 'whisper')
WHISPER_CACHE_DIR = Path(WHISPER_CACHE_DIR)
WHISPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Audio preprocessing settings
AUDIO_PREPROCESSING = {
    'normalize': True,
    'high_pass_filter': 300,    # Hz - remove low frequency noise
    'low_pass_filter': 3400,    # Hz - remove high frequency noise
    'min_silence_len': 1000,    # ms - minimum silence duration
    'silence_threshold': -40,   # dB - silence detection threshold
    'keep_silence': 500,        # ms - keep this much silence around speech
}

# Engine priority for fallback
STT_ENGINE_PRIORITY = [
    'whisper',      # Primary: best accuracy
    'google',       # Secondary: faster, requires internet
    'sphinx'        # Fallback: offline, lower accuracy
]

# Memory management
CLEAR_AUDIO_CACHE_AFTER_PROCESSING = True
MAX_MEMORY_USAGE_MB = int(os.getenv('MAX_MEMORY_USAGE_MB', '2048'))  # 2GB limit

# Logging for production
AUDIO_PROCESSING_LOG_LEVEL = os.getenv('AUDIO_LOG_LEVEL', 'INFO')
AUDIO_PROCESSING_LOG_FILE = os.getenv('AUDIO_LOG_FILE', '/var/log/audio_processing.log')

# Quality vs Speed profiles
AUDIO_QUALITY_PROFILES = {
    'fast': {
        'whisper_model': 'tiny',
        'chunk_length': 20,
        'overlap': 1,
        'noise_reduction': 'none',
        'enhance_speech': False,
        'beam_size': 1,
        'best_of': 1
    },
    'balanced': {
        'whisper_model': 'base',
        'chunk_length': 30,
        'overlap': 2,
        'noise_reduction': 'auto',
        'enhance_speech': True,
        'beam_size': 3,
        'best_of': 3
    },
    'high_quality': {
        'whisper_model': 'small',
        'chunk_length': 45,
        'overlap': 3,
        'noise_reduction': 'strong',
        'enhance_speech': True,
        'beam_size': 5,
        'best_of': 5
    }
}

# Default profile
DEFAULT_QUALITY_PROFILE = os.getenv('DEFAULT_AUDIO_QUALITY', 'balanced')
