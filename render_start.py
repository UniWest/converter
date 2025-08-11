#!/usr/bin/env python
"""
Render.com specific startup script.
Ensures proper port binding on 0.0.0.0 as required by Render.
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main startup function for Render deployment"""
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
    
    # Get port from environment variable (Render sets this automatically)
    port = os.environ.get('PORT', '10000')
    host = '0.0.0.0'  # Required by Render
    
    print(f"🚀 Starting on Render - binding to {host}:{port}")
    
    try:
        # Run migrations
        print("📦 Running database migrations...")
        subprocess.run([
            sys.executable, 'manage.py', 'migrate', '--noinput'
        ], check=True, cwd=Path(__file__).parent)
        
        # Collect static files
        print("📁 Collecting static files...")
        subprocess.run([
            sys.executable, 'manage.py', 'collectstatic', '--noinput'
        ], check=True, cwd=Path(__file__).parent)
        
        # Start with gunicorn for production
        print("🔥 Starting Gunicorn server...")
        gunicorn_cmd = [
            'gunicorn',
            '--bind', f'{host}:{port}',
            '--workers', '2',  # Reduced workers for free tier
            '--threads', '4',
            '--timeout', '300',
            '--max-requests', '1000',
            '--max-requests-jitter', '100',
            '--access-logfile', '-',
            '--error-logfile', '-',
            '--log-level', 'info',
            'converter_site.wsgi:application'
        ]
        
        print(f"📋 Command: {' '.join(gunicorn_cmd)}")
        subprocess.run(gunicorn_cmd, check=True, cwd=Path(__file__).parent)
        
    except FileNotFoundError as e:
        if 'gunicorn' in str(e):
            print("⚠️  Gunicorn not found, installing...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'gunicorn'], check=True)
            print("✅ Gunicorn installed, restarting...")
            # Retry with gunicorn
            subprocess.run([
                'gunicorn',
                '--bind', f'{host}:{port}',
                '--workers', '2',
                '--threads', '4',
                '--timeout', '300',
                'converter_site.wsgi:application'
            ], check=True, cwd=Path(__file__).parent)
        else:
            raise
    except Exception as e:
        print(f"❌ Error with Gunicorn: {e}")
        print("🔄 Falling back to Django runserver...")
        # Fallback to Django dev server
        subprocess.run([
            sys.executable, 'manage.py', 'runserver', f'{host}:{port}'
        ], cwd=Path(__file__).parent)

if __name__ == '__main__':
    main()
