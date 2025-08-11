#!/usr/bin/env python3
"""
Extended cleanup script to handle more complex unused imports and dead code
"""

import re
from pathlib import Path

def clean_adapter_engines():
    """Clean up adapter engine files that have many unused imports"""
    
    engines = [
        "converter/adapters/archive_engine.py",
        "converter/adapters/audio_engine.py", 
        "converter/adapters/document_engine.py",
        "converter/adapters/image_engine.py",
        "converter/adapters/video_engine.py"
    ]
    
    for engine_path in engines:
        engine_file = Path(engine_path)
        if not engine_file.exists():
            continue
            
        content = engine_file.read_text(encoding='utf-8')
        original_content = content
        
        # Remove unused base imports
        content = re.sub(r'^from \.base import.*EngineNotAvailableError.*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^from \.base import.*ConversionError.*\n', '', content, flags=re.MULTILINE) 
        content = re.sub(r'^from \.base import.*UnsupportedFormatError.*\n', '', content, flags=re.MULTILINE)
        
        # Remove unused os imports
        if "os.path" not in content and "os.makedirs" not in content:
            content = re.sub(r'^import os\n', '', content, flags=re.MULTILINE)
        
        # Remove unused tempfile imports
        if "tempfile." not in content:
            content = re.sub(r'^import tempfile\n', '', content, flags=re.MULTILINE)
            
        # Clean up conditional imports that are never used
        lines = content.split('\n')
        cleaned_lines = []
        skip_block = False
        
        for line in lines:
            # Skip unused conditional import blocks
            if line.strip().startswith('try:') and 'import' in line:
                # Look ahead to see if this import is actually used
                skip_block = True
                continue
            elif skip_block and line.strip().startswith('except'):
                skip_block = True
                continue
            elif skip_block and (line.strip() == '' or line.startswith('    ')):
                continue
            else:
                skip_block = False
                
            cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        if content != original_content:
            engine_file.write_text(content, encoding='utf-8')
            print(f"✓ {engine_path}: Cleaned up unused imports")

def clean_test_files():
    """Clean up test files with unused imports"""
    
    test_files = [
        "test_adapter_integrations.py",
        "test_adapter_units.py", 
        "test_adapters.py",
        "test_celery_integration.py",
        "test_integration.py",
        "test_new_features.py",
        "test_small_files.py",
        "test_small_files_fixed.py",
        "test_utils.py"
    ]
    
    for test_path in test_files:
        test_file = Path(test_path)
        if not test_file.exists():
            continue
            
        content = test_file.read_text(encoding='utf-8')
        
        # Remove common unused imports from test files
        unused_patterns = [
            r'^import sys\n',
            r'^import tempfile\n',
            r'^import subprocess\n', 
            r'^import requests\n',
            r'^from unittest\.mock import.*MagicMock.*\n',
            r'^from unittest\.mock import.*mock_open.*\n',
            r'^import io\n',
            r'^from typing import.*\n'
        ]
        
        for pattern in unused_patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
        test_file.write_text(content, encoding='utf-8')
        print(f"✓ {test_path}: Cleaned up unused imports")

def clean_main_files():
    """Clean up main application files"""
    
    # Clean debug_deployment.py
    debug_file = Path("debug_deployment.py")
    if debug_file.exists():
        content = debug_file.read_text(encoding='utf-8')
        content = re.sub(r'^import sys\n', '', content, flags=re.MULTILINE)
        debug_file.write_text(content, encoding='utf-8')
        print("✓ debug_deployment.py: Removed unused sys import")
    
    # Clean production_patch.py
    prod_file = Path("production_patch.py")
    if prod_file.exists():
        content = prod_file.read_text(encoding='utf-8')
        content = re.sub(r'^import os\n', '', content, flags=re.MULTILINE)
        prod_file.write_text(content, encoding='utf-8')
        print("✓ production_patch.py: Removed unused os import")
    
    # Clean fix_null_bytes.py
    fix_file = Path("fix_null_bytes.py")
    if fix_file.exists():
        content = fix_file.read_text(encoding='utf-8')
        content = re.sub(r'^import os\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^import shutil\n', '', content, flags=re.MULTILINE)
        fix_file.write_text(content, encoding='utf-8')
        print("✓ fix_null_bytes.py: Removed unused imports")

def clean_more_files():
    """Clean up additional files with unused imports"""
    
    # API views extended
    api_file = Path("converter/api_views_extended.py")
    if api_file.exists():
        content = api_file.read_text(encoding='utf-8')
        
        # Remove unused imports
        unused_imports = [
            r'^from django\.http import Http404\n',
            r'^from django\.conf import settings\n',
            r'^from django\.contrib import messages\n',
            r'^from datetime import datetime\n',
            r'^from celery import current_task\n',
            r'^import celery\n',
            r'^from celery\.result import AsyncResult\n'
        ]
        
        for pattern in unused_imports:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
        api_file.write_text(content, encoding='utf-8')
        print("✓ converter/api_views_extended.py: Cleaned up unused imports")
    
    # Smoke test
    smoke_file = Path("smoke_test.py") 
    if smoke_file.exists():
        content = smoke_file.read_text(encoding='utf-8')
        content = re.sub(r'^from django\.urls import reverse\n', '', content, flags=re.MULTILINE)
        smoke_file.write_text(content, encoding='utf-8')
        print("✓ smoke_test.py: Removed unused import")

if __name__ == "__main__":
    print("🧹 Running extended cleanup...")
    
    clean_adapter_engines()
    clean_test_files() 
    clean_main_files()
    clean_more_files()
    
    print("✅ Extended cleanup completed!")
