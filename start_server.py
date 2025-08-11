#!/usr/bin/env python
"""
Startup script for deployment platforms like Render, Heroku, etc.
Uses the PORT setting from Django settings and handles migrations.
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
    """Main startup function"""
    try:
        # Import Django settings after setting the module
        import django
        django.setup()
        from django.conf import settings
        
        # Get port from settings
        port = settings.PORT
        host = '0.0.0.0'  # Listen on all interfaces for deployment
        
        print(f"Starting Django development server on {host}:{port}")
        print("Press CTRL+C to quit.")
        
        # Run migrations first
        print("Running database migrations...")
        subprocess.run([
            sys.executable, 'manage.py', 'migrate', '--noinput'
        ], check=True)
        
        # Collect static files in production
        if not settings.DEBUG:
            print("Collecting static files...")
            subprocess.run([
                sys.executable, 'manage.py', 'collectstatic', '--noinput'
            ], check=True)
        
        # Start the server
        subprocess.run([
            sys.executable, 'manage.py', 'runserver', f'{host}:{port}'
        ], check=True)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
