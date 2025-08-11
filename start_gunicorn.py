#!/usr/bin/env python
"""
Production startup script using Gunicorn for deployment platforms.
Uses the PORT setting from Django settings.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add the project directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')

def main():
    """Main startup function for production"""
    try:
        # Import Django settings after setting the module
        import django
        django.setup()
        from django.conf import settings
        
        # Get port from settings
        port = settings.PORT
        host = '0.0.0.0'  # Listen on all interfaces for deployment
        
        print(f"Starting Gunicorn server on {host}:{port}")
        
        # Run migrations first
        print("Running database migrations...")
        subprocess.run([
            sys.executable, 'manage.py', 'migrate', '--noinput'
        ], check=True)
        
        # Collect static files
        print("Collecting static files...")
        subprocess.run([
            sys.executable, 'manage.py', 'collectstatic', '--noinput'
        ], check=True)
        
        # Start Gunicorn server
        gunicorn_cmd = [
            'gunicorn',
            '--bind', f'{host}:{port}',
            '--workers', '3',
            '--timeout', '300',  # 5 minutes timeout for video processing
            '--max-requests', '1000',
            '--max-requests-jitter', '100',
            '--preload',
            '--access-logfile', '-',
            '--error-logfile', '-',
            'converter_site.wsgi:application'
        ]
        
        print(f"Command: {' '.join(gunicorn_cmd)}")
        subprocess.run(gunicorn_cmd, check=True)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except FileNotFoundError:
        print("Gunicorn not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'gunicorn'], check=True)
        print("Gunicorn installed. Please run the script again.")
    except Exception as e:
        print(f"Error starting server: {e}")
        # Fallback to Django dev server
        print("Falling back to Django development server...")
        subprocess.run([
            sys.executable, 'manage.py', 'runserver', f'{host}:{port}'
        ])

if __name__ == '__main__':
    main()
