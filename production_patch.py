# production_settings.py - 4>?>;=5=85 : settings.py 4;O ?@>40:H5=0

# 1=>2;O5< FFMPEG_BINARY 4;O Railway
FFMPEG_BINARY = 'ffmpeg'  # Railway 8<55B ffmpeg 2 PATH

# 57>?0A=K5 =0AB@>9:8 4;O ?@>40:H5=0
SECURE_SSL_REDIRECT = False  # Railway A0< >1@010BK205B SSL
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CORS 4;O Railway
CORS_ALLOWED_ORIGINS = []  # Railway 02B><0B8G5A:8 =0AB@>8B
CSRF_TRUSTED_ORIGINS = []

# 0AB@>9:8 4;O AB0B8G5A:8E D09;>2
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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