#!/usr/bin/env python3
"""
Final cleanup script to remove all remaining unused imports, especially conditional imports
"""

import re
from pathlib import Path

def clean_conditional_imports():
    """Remove unused conditional imports from adapter files"""
    
    # Archive engine
    archive_file = Path("converter/adapters/archive_engine.py")
    if archive_file.exists():
        content = archive_file.read_text(encoding='utf-8')
        
        # Remove unused conditional imports
        patterns_to_remove = [
            r'\s*try:\s*\n\s*import zipfile\s*\n\s*except ImportError:\s*\n\s*zipfile = None\s*\n',
            r'\s*try:\s*\n\s*import tarfile\s*\n\s*except ImportError:\s*\n\s*tarfile = None\s*\n',
            r'\s*try:\s*\n\s*import gzip\s*\n\s*except ImportError:\s*\n\s*gzip = None\s*\n',
            r'\s*try:\s*\n\s*import bz2\s*\n\s*except ImportError:\s*\n\s*bz2 = None\s*\n',
            r'\s*try:\s*\n\s*import lzma\s*\n\s*except ImportError:\s*\n\s*lzma = None\s*\n',
            r'\s*try:\s*\n\s*import py7zr\s*\n\s*except ImportError:\s*\n\s*py7zr = None\s*\n',
            r'\s*try:\s*\n\s*import rarfile\s*\n\s*except ImportError:\s*\n\s*rarfile = None\s*\n'
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '\n', content, flags=re.DOTALL)
            
        archive_file.write_text(content, encoding='utf-8')
        print("✓ converter/adapters/archive_engine.py: Removed conditional imports")
    
    # Audio engine
    audio_file = Path("converter/adapters/audio_engine.py")
    if audio_file.exists():
        content = audio_file.read_text(encoding='utf-8')
        
        patterns_to_remove = [
            r'\s*try:\s*\n\s*import pydub\s*\n\s*except ImportError:\s*\n\s*pydub = None\s*\n',
            r'\s*try:\s*\n\s*import simpleaudio\s*\n\s*except ImportError:\s*\n\s*simpleaudio = None\s*\n'
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '\n', content, flags=re.DOTALL)
            
        audio_file.write_text(content, encoding='utf-8')
        print("✓ converter/adapters/audio_engine.py: Removed conditional imports")
    
    # Document engine
    doc_file = Path("converter/adapters/document_engine.py")
    if doc_file.exists():
        content = doc_file.read_text(encoding='utf-8')
        
        patterns_to_remove = [
            r'\s*try:\s*\n\s*import PyPDF2\s*\n\s*except ImportError:\s*\n.*?\n',
            r'\s*try:\s*\n\s*import PyPDF4 as PyPDF2\s*\n\s*except ImportError:\s*\n.*?\n',
            r'\s*try:\s*\n\s*import docx\s*\n\s*except ImportError:\s*\n.*?\n',
            r'\s*try:\s*\n\s*import openpyxl\s*\n\s*except ImportError:\s*\n.*?\n',
            r'\s*try:\s*\n\s*import pypandoc\s*\n\s*except ImportError:\s*\n.*?\n',
            r'\s*try:\s*\n\s*import bs4\s*\n\s*except ImportError:\s*\n.*?\n',
            r'\s*try:\s*\n\s*import markdown\s*\n\s*except ImportError:\s*\n.*?\n'
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '\n', content, flags=re.DOTALL)
            
        doc_file.write_text(content, encoding='utf-8')
        print("✓ converter/adapters/document_engine.py: Removed conditional imports")
    
    # Image engine
    image_file = Path("converter/adapters/image_engine.py")
    if image_file.exists():
        content = image_file.read_text(encoding='utf-8')
        
        patterns_to_remove = [
            r'\s*try:\s*\n\s*from PIL import Image\s*\n\s*except ImportError:\s*\n.*?\n',
            r'\s*try:\s*\n\s*import cv2\s*\n\s*except ImportError:\s*\n.*?\n',
            r'\s*from PIL import Image, ImageEnhance\s*\n'
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '\n', content, flags=re.DOTALL)
            
        image_file.write_text(content, encoding='utf-8')
        print("✓ converter/adapters/image_engine.py: Removed conditional imports")
    
    # Video engine  
    video_file = Path("converter/adapters/video_engine.py")
    if video_file.exists():
        content = video_file.read_text(encoding='utf-8')
        
        patterns_to_remove = [
            r'\s*try:\s*\n\s*import moviepy.*\n\s*except ImportError:\s*\n.*?\n'
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '\n', content, flags=re.DOTALL)
            
        video_file.write_text(content, encoding='utf-8')
        print("✓ converter/adapters/video_engine.py: Removed conditional imports")

def clean_remaining_unused_imports():
    """Clean up remaining simple unused imports"""
    
    files_to_clean = {
        "check_environment.py": [
            r'^.*magic.*\n',
            r'^.*cv2.*\n', 
            r'^.*PIL\.Image.*\n',
            r'^.*converter_settings\.BINARY_PATHS.*\n'
        ],
        "converter/admin.py": [r'^from django\.utils import timezone\n'],
        "converter/api_views_extended.py": [
            r'^from django\.http import Http404\n',
            r'^from datetime import datetime\n'
        ],
        "converter/management/commands/cleanup_old_files.py": [
            r'^import os\n',
            r'^import shutil\n',
            r'^from django\.core\.management\.base import CommandError\n'
        ],
        "converter/tests.py": [
            r'^from unittest\.mock import MagicMock\n',
            r'^from django\.core\.files\.uploadedfile import InMemoryUploadedFile\n',
            r'^from django\.conf import settings\n',
            r'^from io import BytesIO\n'
        ],
        "converter/utils.py": [
            r'^from django\.core\.files\.storage import default_storage\n',
            r'^from django\.core\.files\.base import ContentFile\n',
            r'.*PIL\.ImageEnhance.*\n',
            r'.*PIL\.ImageFilter.*\n'
        ],
        "converter_site/railway_settings.py": [
            r'^import os\n',
            r'^from \.settings import \*\n'
        ],
        "converter_site/tasks.py": [
            r'^import tempfile\n',
            r'^import subprocess\n',
            r'^import shutil\n',
            r'^from datetime import timedelta\n',
            r'^from pathlib import Path\n',
            r'^from typing import.*\n',
            r'^from django\.core\.files\.storage import default_storage\n',
            r'^from django\.core\.files\.base import ContentFile\n'
        ]
    }
    
    for file_path, patterns in files_to_clean.items():
        file_obj = Path(file_path)
        if not file_obj.exists():
            continue
            
        content = file_obj.read_text(encoding='utf-8')
        
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
        file_obj.write_text(content, encoding='utf-8')
        print(f"✓ {file_path}: Cleaned up unused imports")

def clean_test_files_final():
    """Final cleanup of test files"""
    
    test_files = [
        "run_adapter_tests.py",
        "run_adapter_tests_fixed.py", 
        "run_tests_final.py",
        "test_adapter_integrations.py",
        "test_adapter_units.py",
        "test_celery_integration.py",
        "test_small_files.py", 
        "test_small_files_fixed.py",
        "tests/run_all_tests.py",
        "tests/test_audio_generator.py",
        "tests/test_celery_api.py",
        "tests/test_stt_functionality.py",
        "tests/test_ui_functionality.py"
    ]
    
    for test_path in test_files:
        test_file = Path(test_path)
        if not test_file.exists():
            continue
            
        content = test_file.read_text(encoding='utf-8')
        
        # Remove unused imports with more comprehensive patterns
        unused_patterns = [
            r'^import subprocess\n',
            r'^import os\n',
            r'^import tempfile\n', 
            r'^import json\n',
            r'^import requests\n',
            r'^from typing import.*\n',
            r'^from django\.urls import reverse\n',
            r'^from django\.conf import settings\n',
            r'^from selenium\..*\n',
            r'^from celery\.exceptions.*\n',
            r'^from converter\.adapters\.base import.*\n',
            r'^from converter\.tasks import.*\n',
            r'^from converter\.models import.*\n',
            r'.*PIL\.Image.*\n'
        ]
        
        for pattern in unused_patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
        test_file.write_text(content, encoding='utf-8')
        
    print("✓ Test files: Cleaned up unused imports")

def clean_debug_files():
    """Clean debug and utility files"""
    
    debug_file = Path("debug_deployment.py")
    if debug_file.exists():
        content = debug_file.read_text(encoding='utf-8')
        content = re.sub(r'.*converter_site\.wsgi\.application.*\n', '', content)
        debug_file.write_text(content, encoding='utf-8')
        print("✓ debug_deployment.py: Cleaned unused import")
    
    smoke_file = Path("smoke_test.py")
    if smoke_file.exists():
        content = smoke_file.read_text(encoding='utf-8')
        content = re.sub(r'.*converter\.models\.ConversionTask.*\n', '', content)
        smoke_file.write_text(content, encoding='utf-8')
        print("✓ smoke_test.py: Cleaned unused import")

if __name__ == "__main__":
    print("🧹 Running final cleanup...")
    
    clean_conditional_imports()
    clean_remaining_unused_imports() 
    clean_test_files_final()
    clean_debug_files()
    
    print("✅ Final cleanup completed!")
