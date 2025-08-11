# railway_settings.py - A?5F80;L=> 4;O Railway

# 5@5>?@545;O5< =0AB@>9:8 4;O Railway
DEBUG = False
ALLOWED_HOSTS = ['*']

# #18@05< ?@>1;5<=K5 CORS =0AB@>9:8
CORS_ALLOWED_ORIGINS = []
CSRF_TRUSTED_ORIGINS = ['https://*.railway.app']

# FFmpeg 4;O Railway
FFMPEG_BINARY = 'ffmpeg'

# #?@>I05< INSTALLED_APPS - C18@05< ?@>1;5<=K5 ?@8;>65=8O
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'converter',
]

# >38@>20=85
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}