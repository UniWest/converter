#!/usr/bin/env python3
"""
Debug script to check for common deployment issues
"""
import os
import sys
from pathlib import Path

def check_file_encoding(filepath):
    """Check if file contains null bytes"""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            if b'\x00' in content:
                return False, "Contains null bytes"
        
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read()
            return True, "OK"
    except UnicodeDecodeError:
        return False, "Unicode decode error"
    except Exception as e:
        return False, str(e)

def main():
    print("Django Deployment Debug Check")
    print("=" * 40)
    
    # Check critical files
    critical_files = [
        'manage.py',
        'converter_site/wsgi.py',
        'converter_site/settings.py',
        'Procfile',
        'build.sh',
        'requirements.txt'
    ]
    
    base_dir = Path(__file__).parent
    
    for filepath in critical_files:
        full_path = base_dir / filepath
        if full_path.exists():
            is_ok, message = check_file_encoding(full_path)
            status = "✓" if is_ok else "✗"
            print(f"{status} {filepath}: {message}")
        else:
            print(f"✗ {filepath}: File not found")
    
    # Check Django imports
    print("\nDjango Import Check:")
    print("-" * 20)
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
        import django
        django.setup()
        print("✓ Django imports successfully")
        
        from converter_site.wsgi import application
        print("✓ WSGI application loads successfully")
        
    except Exception as e:
        print(f"✗ Django import error: {e}")
    
    # Check environment variables
    print("\nEnvironment Variables:")
    print("-" * 20)
    env_vars = ['SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS', 'PORT']
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        if var == 'SECRET_KEY' and value != 'Not set':
            value = value[:10] + "..." # Hide secret key
        print(f"{var}: {value}")

if __name__ == "__main__":
    main()
