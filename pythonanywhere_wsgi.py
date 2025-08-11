"""
WSGI config for PythonAnywhere deployment.
Copy this content to your WSGI configuration file on PythonAnywhere.
"""

import os
import sys

# Add your project directory to sys.path
path = '/home/yourusername/mysite'  # замените на ваш путь
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'converter_site.settings'

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
