#!/usr/bin/env bash
set -euo pipefail

# Default port if not provided by platform
PORT="${PORT:-8000}"

# Print environment summary (non-sensitive)
echo "Starting Django with gunicorn on port ${PORT}"
python --version
pip --version || true

# Apply migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput || true

# Start gunicorn
exec gunicorn converter_site.wsgi --bind 0.0.0.0:"${PORT}" --log-file -
