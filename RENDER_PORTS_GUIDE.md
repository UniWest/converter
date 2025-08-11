# Render Ports Configuration Guide

## Port Overview

When deploying to Render, proper port configuration is critical for your web service to work correctly.

## Correct Port Configuration

### Default Port: 10000
```bash
# In your Procfile
web: gunicorn converter_site.wsgi:application --bind 0.0.0.0:$PORT --timeout 120
```

- **PORT** environment variable is automatically set to **10000** by Render
- Your app MUST bind to `0.0.0.0:$PORT` to receive HTTP requests
- The `$PORT` variable allows Render to route traffic to your application

## Reserved Ports (DO NOT USE)

These ports are reserved by Render and will cause deployment failures:

- **18012** - Reserved by Render infrastructure
- **18013** - Reserved by Render infrastructure  
- **19099** - Reserved by Render infrastructure

### What happens if you use reserved ports:
```
==> No open ports detected, continuing to scan...
==> Docs on specifying a port: https://render.com/docs/web-services#port-binding
```

## Troubleshooting "No Open Ports" Error

### Common Causes:
1. **Hardcoded port** - Using fixed port instead of `$PORT` variable
2. **Wrong binding address** - Not binding to `0.0.0.0`
3. **Reserved ports** - Trying to use 18012, 18013, or 19099
4. **Application not starting** - Dependency or configuration issues
5. **Null bytes in files** - Encoding issues causing Python syntax errors

### Solutions:
```bash
# CORRECT - Use PORT environment variable
gunicorn app:application --bind 0.0.0.0:$PORT

# WRONG - Hardcoded port
gunicorn app:application --bind 0.0.0.0:8000

# WRONG - Wrong binding address
gunicorn app:application --bind 127.0.0.1:$PORT

# WRONG - Reserved port
gunicorn app:application --bind 0.0.0.0:18012
```

## Port Configuration Checklist

- [ ] Using `$PORT` environment variable in start command
- [ ] Binding to `0.0.0.0:$PORT` (not localhost or 127.0.0.1)
- [ ] Not using reserved ports (18012, 18013, 19099)
- [ ] Application starts successfully without errors
- [ ] All dependencies installed correctly
- [ ] No null bytes in Python files

## Your Current Configuration

Your project is configured correctly:

**Procfile:**
```
web: gunicorn converter_site.wsgi:application --bind 0.0.0.0:$PORT --timeout 120
```

**Build Script (build.sh):**
```bash
#!/bin/bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
```

This configuration should work perfectly with Render's port system!
