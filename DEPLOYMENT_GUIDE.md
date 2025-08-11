# Django Converter Site - Deployment and Configuration Guide

This guide covers the complete setup of static files, media files, security settings, and automated cleanup for the Django Converter Site.

## 📋 Table of Contents

1. [Static and Media Files Configuration](#static-and-media-files-configuration)
2. [Security Settings](#security-settings)
3. [Upload Limits Configuration](#upload-limits-configuration)
4. [Production Deployment with Nginx](#production-deployment-with-nginx)
5. [Automated Cleanup Setup](#automated-cleanup-setup)
6. [Environment Configuration](#environment-configuration)
7. [SSL and HTTPS Setup](#ssl-and-https-setup)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)

## 🗂️ Static and Media Files Configuration

### Development Setup

The application is configured to serve static and media files in development mode:

```python
# settings.py
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

### Production with WhiteNoise

For simple production deployments, WhiteNoise is already configured:

```python
# In MIDDLEWARE
'whitenoise.middleware.WhiteNoiseMiddleware',

# For production static files
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### AWS S3 Configuration (Optional)

For production with S3 storage, uncomment and configure these settings in `settings.py`:

```python
# S3 Configuration (uncomment for production)
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
```

## 🔒 Security Settings

### ALLOWED_HOSTS Configuration

Configure allowed hosts for your environment:

```bash
# Development
ALLOWED_HOSTS=*

# Production
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

### CSRF Protection

Configure trusted origins:

```bash
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### Production Security Headers

The following security settings are automatically applied in production:

- SSL Redirect
- HSTS (HTTP Strict Transport Security)
- Content Type Options
- XSS Protection
- Secure Cookies

## 📤 Upload Limits Configuration

### Django Settings

Configure upload limits in your environment:

```bash
# Maximum upload size in MB
MAX_UPLOAD_SIZE=500
FILE_UPLOAD_MAX_MEMORY_SIZE=10
DATA_UPLOAD_MAX_MEMORY_SIZE=10
```

### Nginx Configuration

Ensure your Nginx configuration matches Django limits:

```nginx
# In server block
client_max_body_size 500M;  # Must match Django's MAX_UPLOAD_SIZE
client_body_timeout 120s;
client_header_timeout 120s;
```

## 🌐 Production Deployment with Nginx

### 1. Install Nginx Configuration

Copy the provided Nginx configuration:

```bash
sudo cp deployment/nginx.conf /etc/nginx/sites-available/django-converter
sudo ln -s /etc/nginx/sites-available/django-converter /etc/nginx/sites-enabled/
```

### 2. Update Configuration

Edit the configuration file:

```bash
sudo nano /etc/nginx/sites-available/django-converter
```

Update the following paths:
- `your-domain.com` → your actual domain
- `/var/www/your-app` → your project path
- SSL certificate paths
- Static and media file paths

### 3. Test and Reload

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4. SSL Certificate Setup

For Let's Encrypt certificates:

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## 🧹 Automated Cleanup Setup

### 1. Make Cleanup Script Executable

```bash
chmod +x scripts/cleanup_cron.sh
```

### 2. Update Script Paths

Edit `scripts/cleanup_cron.sh` and update:
- `PROJECT_DIR="/var/www/your-app"`
- `PYTHON_PATH="/var/www/your-app/venv/bin/python"`

### 3. Install Cron Jobs

```bash
crontab -e
```

Add the following line for daily cleanup at 2:00 AM:

```cron
0 2 * * * /var/www/your-app/scripts/cleanup_cron.sh >/dev/null 2>&1
```

### 4. Manual Cleanup Commands

You can also run cleanup manually:

```bash
# Clean files older than 7 days
python manage.py cleanup_old_files --days 7

# Clean temporary files only
python manage.py cleanup_old_files --temp-only

# Clean all failed tasks
python manage.py cleanup_old_files --all-failed

# Dry run (show what would be deleted)
python manage.py cleanup_old_files --days 7 --dry-run
```

## ⚙️ Environment Configuration

### 1. Create Production Environment File

```bash
cp .env.production.sample .env
```

### 2. Configure Essential Settings

Edit `.env` with your production values:

```bash
SECRET_KEY=your-generated-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### 3. Database Configuration (Optional)

For PostgreSQL production database:

```bash
# Install PostgreSQL and create database
sudo apt install postgresql postgresql-contrib
sudo -u postgres createdb converter_db
sudo -u postgres createuser converter_user

# Add to .env
DATABASE_URL=postgresql://converter_user:password@localhost:5432/converter_db
```

## 🔐 SSL and HTTPS Setup

### 1. Let's Encrypt (Recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 2. Auto-renewal Setup

```bash
# Add to crontab
0 5 * * * /usr/bin/certbot renew --quiet --no-self-upgrade >/dev/null 2>&1
```

## 📊 Monitoring and Maintenance

### 1. Log Monitoring

Logs are configured to be written to:
- Application logs: `/var/log/django.log` (production)
- Cleanup logs: `/var/log/django_cleanup.log`
- Nginx logs: `/var/log/nginx/`

### 2. Disk Space Monitoring

The cleanup script includes disk space monitoring. For additional monitoring:

```bash
# Add to crontab for email alerts
0 6 * * * /bin/bash -c 'USAGE=$(df /var/www/your-app | awk "NR==2 {print \$5}" | sed "s/%//"); if [ \$USAGE -gt 85 ]; then echo "Disk usage: \$USAGE%" | mail -s "High Disk Usage" admin@your-domain.com; fi'
```

### 3. Health Checks

The application includes a health check endpoint at `/health/`. Use it for monitoring:

```bash
# Check application health
curl -f http://your-domain.com/health/
```

### 4. Database Maintenance (PostgreSQL)

For PostgreSQL databases, add monthly maintenance:

```bash
# Add to crontab (monthly on 1st day at 4:00 AM)
0 4 1 * * /var/www/your-app/venv/bin/python /var/www/your-app/manage.py dbshell -c "VACUUM ANALYZE;"
```

## 🚀 Deployment Checklist

### Pre-deployment

- [ ] Configure environment variables in `.env`
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
- [ ] Set up SSL certificates
- [ ] Configure database (if not using SQLite)
- [ ] Update Nginx configuration paths

### Post-deployment

- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Run database migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Test file upload functionality
- [ ] Set up automated cleanup cron jobs
- [ ] Configure log rotation
- [ ] Test SSL configuration
- [ ] Set up monitoring and alerting

### Regular Maintenance

- [ ] Monitor disk space usage
- [ ] Check application logs for errors
- [ ] Verify cleanup cron jobs are running
- [ ] Monitor SSL certificate expiration
- [ ] Update dependencies regularly
- [ ] Backup database and media files
- [ ] Test disaster recovery procedures

## 📞 Troubleshooting

### Common Issues

1. **Files not uploading**: Check nginx `client_max_body_size` matches Django `MAX_UPLOAD_SIZE`
2. **Static files not loading**: Run `python manage.py collectstatic` and check Nginx configuration
3. **Permission errors**: Ensure proper ownership and permissions on media directories
4. **Cleanup not working**: Check cron job logs and script permissions

### Debug Commands

```bash
# Check Django configuration
python manage.py check --deploy

# Test cleanup command
python manage.py cleanup_old_files --dry-run --verbosity=2

# Check file permissions
ls -la media/ temp/ staticfiles/

# Test Nginx configuration
sudo nginx -t
```

For additional support, check the application logs and Django documentation.
