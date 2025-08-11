# Render Environment Variables Configuration

Set these environment variables in your Render service dashboard:

## Required Variables:
```
SECRET_KEY=your-secret-key-here-generate-new-one
DEBUG=False
ALLOWED_HOSTS=*
DATABASE_URL=sqlite:///tmp/db.sqlite3
PYTHONPATH=/opt/render/project/src
```

## Optional but Recommended:
```
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
STT_ENGINE=whisper
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
FFMPEG_BINARY=ffmpeg
MEDIA_MAX_SIZE=500
AUDIO_MAX_DURATION=3600
LOG_LEVEL=INFO
```

## Security (Production):
```
SECURE_SSL_REDIRECT=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS=DENY
```

## Port Configuration:

### Default Port:
- **PORT=10000** (automatically set by Render)
- Your app binds to `0.0.0.0:$PORT` (configured in Procfile)

### Reserved Ports (DO NOT USE):
- **18012** - Reserved by Render
- **18013** - Reserved by Render  
- **19099** - Reserved by Render

Warning: If you try to bind to reserved ports, your deployment will fail with "No open ports detected" error.

## How to set in Render:
1. Go to your service dashboard
2. Click "Environment" tab
3. Add each variable with "Add Environment Variable"
4. Click "Save Changes"
5. Your service will automatically redeploy

## Troubleshooting Port Issues:
- Use PORT environment variable: `--bind 0.0.0.0:$PORT`
- Default port 10000 works automatically
- Avoid reserved ports: 18012, 18013, 19099
- Don't hardcode ports in your application
