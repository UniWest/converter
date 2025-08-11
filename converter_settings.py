# -*- coding: utf-8 -*-
"""
Настройки конвертера файлов
Пути к внешним утилитам для обработки различных форматов
"""

import os

# Базовые пути к утилитам
BINARY_PATHS = {
    # FFmpeg для видео/аудио
    'ffmpeg': r'C:\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe',
    'ffprobe': r'C:\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe',
    
    # ImageMagick для изображений
    'magick': r'C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe',
    'convert': r'C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe',  # В новых версиях convert = magick
    
    # LibreOffice для документов
    'soffice': r'C:\Program Files\LibreOffice\program\soffice.exe',
    
    # 7-Zip для архивов  
    '7z': r'C:\Program Files\7-Zip\7z.exe',
}

# Поддерживаемые форматы по категориям (аналогично Convertio)
SUPPORTED_FORMATS = {
    'video': [
        'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', '3gp', 'mpg', 'mpeg',
        'asf', 'vob', 'ts', 'm4v', 'rm', 'rmvb', 'ogv', 'divx', 'xvid'
    ],
    'audio': [
        'mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'ac3', 'aiff', 'au', 'm4a',
        'mp2', 'opus', 'amr', 'ra', 'ape', 'caf', 'dts', 'mka', 'tak', 'tta'
    ],
    'image': [
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'svg', 'ico',
        'psd', 'raw', 'cr2', 'nef', 'arw', 'orf', 'rw2', 'pef', 'srw', 'dng'
    ],
    'document': [
        'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'pages', 'tex', 'wpd', 'wps',
        'xls', 'xlsx', 'ods', 'numbers', 'csv', 'tsv', 'ppt', 'pptx', 'odp', 'key'
    ],
    'archive': [
        'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'lzma', 'iso', 'dmg',
        'cab', 'deb', 'rpm', 'msi', 'exe', 'apk', 'jar'
    ],
    'ebook': [
        'epub', 'mobi', 'azw', 'azw3', 'fb2', 'lit', 'pdb', 'tcr', 'html', 'txt'
    ],
    'presentation': [
        'ppt', 'pptx', 'odp', 'key', 'pps', 'ppsx', 'pot', 'potx'
    ],
    'font': [
        'ttf', 'otf', 'woff', 'woff2', 'eot', 'svg', 'pfb', 'pfm'
    ]
}

# Настройки качества конвертации
QUALITY_SETTINGS = {
    'video': {
        'high': {'crf': 18, 'preset': 'slow'},
        'medium': {'crf': 23, 'preset': 'medium'},
        'low': {'crf': 28, 'preset': 'fast'}
    },
    'audio': {
        'high': {'bitrate': '320k'},
        'medium': {'bitrate': '192k'},
        'low': {'bitrate': '128k'}
    },
    'image': {
        'high': {'quality': 95},
        'medium': {'quality': 85},
        'low': {'quality': 70}
    }
}

# Максимальные размеры файлов (в байтах)
MAX_FILE_SIZES = {
    'free_user': 100 * 1024 * 1024,  # 100MB
    'premium_user': 1 * 1024 * 1024 * 1024,  # 1GB
}

# Временные директории
TEMP_DIRS = {
    'upload': 'temp/uploads',
    'processing': 'temp/processing', 
    'output': 'temp/outputs'
}

# Redis настройки для Celery
REDIS_URL = 'redis://localhost:6379/0'
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

def check_binary_availability():
    """Проверяет доступность всех необходимых бинарников"""
    status = {}
    for name, path in BINARY_PATHS.items():
        status[name] = {
            'path': path,
            'available': os.path.exists(path),
            'executable': os.access(path, os.X_OK) if os.path.exists(path) else False
        }
    return status

if __name__ == '__main__':
    # Тест доступности утилит
    print("Проверка доступности утилит конвертации:")
    print("=" * 50)
    
    status = check_binary_availability()
    for name, info in status.items():
        status_text = "✓ OK" if info['available'] and info['executable'] else "✗ MISSING"
        print(f"{name:12} | {status_text:8} | {info['path']}")
    
    print("\nПоддерживаемые форматы:")
    print("=" * 50)
    for category, formats in SUPPORTED_FORMATS.items():
        print(f"{category:12} | {len(formats):3} форматов | {', '.join(formats[:10])}" + 
              ("..." if len(formats) > 10 else ""))
