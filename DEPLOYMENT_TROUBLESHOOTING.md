# Deployment Troubleshooting Guide

This guide helps you resolve common deployment issues with the Django Video Converter application.

## 🚨 Common Deployment Issues & Solutions

### Issue 1: Logging Configuration Error

**Error:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/app/logs/django.log'
ValueError: Unable to configure handler 'file'
```

**Solution:**
This has been fixed in the latest version. The logging configuration now:
- Creates the `logs` directory automatically
- Tests write permissions before enabling file logging
- Falls back to console-only logging if file logging fails
- Works in both development and production environments

### Issue 2: Port Binding Issues

**Error:**
```
==> No open ports detected, continuing to scan...
==> Docs on specifying a port: https://render.com/docs/web-services#port-binding
```

**Solution:**
We've added proper port binding configuration:

1. **PORT Environment Variable:** The app now reads the `PORT` environment variable automatically
2. **Startup Scripts:** Use the provided startup scripts that handle port binding correctly:
   - `start_server.py` - For development/simple deployment
   - `start_gunicorn.py` - For production deployment with Gunicorn

## 🛠 Deployment Instructions

### For Render.com

**IMPORTANT:** Use these exact settings to avoid port binding issues:

1. **Build Command:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Command:**
   ```bash
   python render_start.py
   ```

3. **Environment Variables (REQUIRED):**
   ```bash
   DEBUG=False
   SECRET_KEY=your-secret-key-here
   ALLOWED_HOSTS=your-app-name.onrender.com
   ```

4. **Optional Environment Variables:**
   ```bash
   FFMPEG_BINARY=ffmpeg  # Uses system ffmpeg
   MAX_UPLOAD_SIZE=500   # MB
   VIDEO_PROCESSING_TIMEOUT=300  # seconds
   ```

**Note:** Do NOT set the PORT variable manually - Render will set it automatically.

### For Heroku

1. **Procfile:**
   ```
   web: python start_gunicorn.py
   release: python manage.py migrate --noinput
   ```

2. **Environment Variables:**
   ```bash
   heroku config:set DEBUG=False
   heroku config:set SECRET_KEY=your-secret-key-here
   heroku config:set FFMPEG_BINARY=ffmpeg
   ```

3. **Buildpacks:**
   ```bash
   heroku buildpacks:add --index 1 heroku/python
   heroku buildpacks:add --index 2 https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
   ```

### For Railway

1. **Deploy Command:**
   ```bash
   python start_gunicorn.py
   ```

2. **Environment Variables:**
   ```bash
   DEBUG=False
   SECRET_KEY=your-secret-key-here
   FFMPEG_BINARY=ffmpeg
   ```

### For DigitalOcean App Platform

1. **Run Command:**
   ```bash
   python start_gunicorn.py
   ```

2. **Build Command:**
   ```bash
   pip install -r requirements.txt
   ```

## 🔧 Manual Port Configuration

If you need to manually specify the port, you can:

1. **Set environment variable:**
   ```bash
   export PORT=8080
   ```

2. **Use Django management command directly:**
   ```bash
   python manage.py runserver 0.0.0.0:$PORT
   ```

3. **Use Gunicorn directly:**
   ```bash
   gunicorn --bind 0.0.0.0:$PORT --workers 3 --timeout 300 converter_site.wsgi:application
   ```

## 📊 System Requirements

### Minimum Requirements:
- Python 3.8+
- 512MB RAM
- 1GB disk space
- FFmpeg installed

### Recommended Requirements:
- Python 3.11+
- 2GB RAM
- 5GB disk space
- FFmpeg with full codec support

## 🧪 Testing Your Deployment

1. **Health Check:**
   ```bash
   curl https://your-app.onrender.com/health/
   ```

2. **Status Check:**
   ```bash
   curl https://your-app.onrender.com/status/
   ```

3. **FFmpeg Test:**
   ```bash
   curl https://your-app.onrender.com/app/status/
   ```

## 📝 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `True` | Enable/disable debug mode |
| `SECRET_KEY` | (auto-generated) | Django secret key |
| `PORT` | `8000` | Server port |
| `ALLOWED_HOSTS` | `*` | Allowed hostnames |
| `FFMPEG_BINARY` | `ffmpeg` (Linux) / `C:\ffmpeg\...` (Windows) | FFmpeg executable path |
| `MAX_UPLOAD_SIZE` | `500` | Max upload size in MB |
| `VIDEO_PROCESSING_TIMEOUT` | `300` | Video processing timeout in seconds |

## 🐛 Debug Mode

For debugging deployment issues, temporarily enable debug mode:

```bash
DEBUG=True python start_server.py
```

**Important:** Never run production with `DEBUG=True`!

## 🆘 Getting Help

If you're still having issues:

1. Check the application logs in your deployment platform
2. Verify all environment variables are set correctly
3. Test FFmpeg installation: `ffmpeg -version`
4. Test the health endpoint: `/health/`
5. Open an issue on GitHub with your deployment logs

## 🚀 Production Optimizations

For better performance in production:

1. **Use Redis for caching:** (Optional - currently disabled)
2. **Enable file logging:** Will auto-enable if directory is writable
3. **Use CDN for static files:** Configure in `settings.py`
4. **Monitor with Sentry:** Uncomment Sentry configuration
5. **Use PostgreSQL:** Install `psycopg2-binary` and configure database

The application is now ready for deployment with these fixes applied! 🎉
