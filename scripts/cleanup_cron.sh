#!/bin/bash

# Automated cleanup script for Django Converter Site
# This script should be run via cron job for regular maintenance

# Configuration
PROJECT_DIR="/var/www/your-app"  # Adjust to your project path
DJANGO_SETTINGS_MODULE="converter_site.settings"
PYTHON_PATH="/var/www/your-app/venv/bin/python"  # Adjust to your Python path
MANAGE_PY="$PROJECT_DIR/manage.py"
LOG_FILE="/var/log/django_cleanup.log"

# Ensure log file exists and has proper permissions
touch "$LOG_FILE"
chmod 644 "$LOG_FILE"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to run Django management command
run_django_command() {
    cd "$PROJECT_DIR"
    export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"
    "$PYTHON_PATH" "$MANAGE_PY" "$@" 2>&1
}

log_message "Starting cleanup process..."

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    log_message "ERROR: Project directory $PROJECT_DIR does not exist"
    exit 1
fi

# Check if Python executable exists
if [ ! -f "$PYTHON_PATH" ]; then
    log_message "ERROR: Python executable $PYTHON_PATH does not exist"
    exit 1
fi

# Check if manage.py exists
if [ ! -f "$MANAGE_PY" ]; then
    log_message "ERROR: manage.py not found at $MANAGE_PY"
    exit 1
fi

# Daily cleanup: Remove files older than 7 days
log_message "Running daily cleanup (7 days)..."
cleanup_output=$(run_django_command cleanup_old_files --days 7)
log_message "Daily cleanup output: $cleanup_output"

# Weekly cleanup: Remove all failed tasks (run on Sundays)
if [ "$(date +%u)" -eq 7 ]; then
    log_message "Running weekly cleanup (failed tasks)..."
    weekly_output=$(run_django_command cleanup_old_files --all-failed)
    log_message "Weekly cleanup output: $weekly_output"
fi

# Clean temporary files daily
log_message "Cleaning temporary files..."
temp_output=$(run_django_command cleanup_old_files --temp-only)
log_message "Temp cleanup output: $temp_output"

# Additional system-level cleanup
log_message "Running system-level cleanup..."

# Clean up system temporary files related to the app
SYSTEM_TEMP="/tmp"
if [ -d "$SYSTEM_TEMP" ]; then
    # Remove Django temporary files older than 1 day
    find "$SYSTEM_TEMP" -name "django_*" -type f -mtime +1 -delete 2>/dev/null
    find "$SYSTEM_TEMP" -name "tmp*" -path "*/media/*" -type f -mtime +1 -delete 2>/dev/null
    log_message "System temporary files cleaned"
fi

# Rotate Django logs if they get too large (> 50MB)
DJANGO_LOG="/var/log/django.log"
if [ -f "$DJANGO_LOG" ] && [ $(stat -f%z "$DJANGO_LOG" 2>/dev/null || stat -c%s "$DJANGO_LOG" 2>/dev/null) -gt 52428800 ]; then
    mv "$DJANGO_LOG" "$DJANGO_LOG.$(date +%Y%m%d)"
    touch "$DJANGO_LOG"
    chmod 644 "$DJANGO_LOG"
    log_message "Django log rotated"
fi

# Clean up old log files (keep last 30 days)
find "$(dirname "$LOG_FILE")" -name "django_cleanup.log.*" -type f -mtime +30 -delete 2>/dev/null
find "$(dirname "$DJANGO_LOG")" -name "django.log.*" -type f -mtime +30 -delete 2>/dev/null

# Check disk space and alert if low
DISK_USAGE=$(df "$PROJECT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    log_message "WARNING: Disk usage is at $DISK_USAGE% - consider manual cleanup"
    
    # Optional: Send email alert (requires mail command)
    # echo "Disk usage on server is at $DISK_USAGE%" | mail -s "High Disk Usage Alert" admin@your-domain.com
fi

# Check if media directory permissions are correct
MEDIA_DIR="$PROJECT_DIR/media"
if [ -d "$MEDIA_DIR" ]; then
    chmod -R 755 "$MEDIA_DIR" 2>/dev/null
    log_message "Media directory permissions checked"
fi

# Check if temp directory permissions are correct
TEMP_DIR="$PROJECT_DIR/temp"
if [ -d "$TEMP_DIR" ]; then
    chmod -R 750 "$TEMP_DIR" 2>/dev/null
    log_message "Temp directory permissions checked"
fi

# Optional: Database maintenance (uncomment if using PostgreSQL)
# log_message "Running database maintenance..."
# psql_output=$(run_django_command dbshell -c "VACUUM ANALYZE;")
# log_message "Database maintenance output: $psql_output"

log_message "Cleanup process completed successfully"

# Keep cleanup log under control (last 1000 lines)
if [ -f "$LOG_FILE" ]; then
    tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

exit 0
