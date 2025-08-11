#!/usr/bin/env python3
"""
Script to fix syntax errors and restore necessary imports that were incorrectly removed
"""

import re
from pathlib import Path

def fix_adapter_imports():
    """Fix adapter files by restoring necessary imports"""
    
    # Fix base imports in adapters
    adapters = [
        "converter/adapters/archive_engine.py",
        "converter/adapters/audio_engine.py", 
        "converter/adapters/document_engine.py",
        "converter/adapters/image_engine.py",
        "converter/adapters/video_engine.py"
    ]
    
    for adapter_path in adapters:
        adapter_file = Path(adapter_path)
        if not adapter_file.exists():
            continue
            
        content = adapter_file.read_text(encoding='utf-8')
        
        # Add missing base imports if they're missing
        if "from .base import" not in content:
            # Find the first non-import line
            lines = content.split('\n')
            import_end_idx = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('import') and not line.strip().startswith('from'):
                    import_end_idx = i
                    break
            
            # Insert the import
            lines.insert(import_end_idx, "from .base import BaseEngine, ConversionResult")
            content = '\n'.join(lines)
        
        adapter_file.write_text(content, encoding='utf-8')
        print(f"✓ {adapter_path}: Fixed base imports")

def fix_typing_imports():
    """Fix typing imports in files that need them"""
    
    # Fix converter_site/tasks.py
    tasks_file = Path("converter_site/tasks.py")
    if tasks_file.exists():
        content = tasks_file.read_text(encoding='utf-8')
        
        # Add typing imports if they're missing and types are used
        if "Dict" in content or "List" in content or "Any" in content:
            if "from typing import" not in content:
                lines = content.split('\n')
                # Find where to insert the import (after other imports)
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('from django') or line.startswith('from celery'):
                        insert_idx = i + 1
                        
                lines.insert(insert_idx, "from typing import Dict, List, Any, Optional, Union, Tuple")
                content = '\n'.join(lines)
                
        tasks_file.write_text(content, encoding='utf-8')
        print("✓ converter_site/tasks.py: Fixed typing imports")

def fix_test_files():
    """Fix test files by restoring necessary imports"""
    
    files_to_fix = {
        "run_adapter_tests.py": ["import os", "import sys", "import subprocess"],
        "run_adapter_tests_fixed.py": ["import os", "import sys", "import subprocess"],
        "run_tests_final.py": ["import os", "import sys", "import subprocess"],
        "test_adapter_integrations.py": ["import os", "import sys", "import tempfile"],
        "test_adapter_units.py": ["import os", "import sys", "import tempfile", "from unittest.mock import Mock, patch", "from converter.adapters.base import BaseEngine, ConversionResult, ConversionError"],
        "test_adapters.py": ["import sys", "import tempfile"],
        "test_integration.py": ["import tempfile", "from unittest.mock import Mock, patch"],
        "test_small_files.py": ["import os", "import sys", "import tempfile", "import io"],
        "test_small_files_fixed.py": ["import os", "import sys", "import tempfile", "import io"],
        "test_utils.py": ["import tempfile"],
        "tests/run_all_tests.py": ["import os", "import json", "from typing import Dict, Any, List"],
        "tests/test_audio_generator.py": ["import os", "import tempfile", "from typing import Dict, List, Any"],
        "tests/test_celery_api.py": ["import os", "import json", "import tempfile", "from django.conf import settings", "from typing import Dict, List, Any"],
        "tests/test_stt_functionality.py": ["import os", "import json", "import tempfile", "from typing import Dict, List, Any"],
        "tests/test_ui_functionality.py": ["import os", "import json", "import tempfile", "from selenium.webdriver.common.by import By", "from selenium.webdriver.support.ui import WebDriverWait", "from selenium.webdriver.support import expected_conditions as EC", "from selenium.common.exceptions import TimeoutException", "from selenium.webdriver.chrome.options import Options as ChromeOptions", "from selenium.webdriver.firefox.options import Options as FirefoxOptions", "from selenium.webdriver.chrome.service import Service as ChromeService", "from selenium.webdriver.firefox.service import Service as FirefoxService", "from typing import Dict, Any"]
    }
    
    for file_path, imports in files_to_fix.items():
        file_obj = Path(file_path)
        if not file_obj.exists():
            continue
            
        content = file_obj.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Find where to insert imports (after existing imports)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('import') and not line.strip().startswith('from'):
                insert_idx = i
                break
        
        # Add missing imports
        for import_stmt in imports:
            if import_stmt not in content:
                lines.insert(insert_idx, import_stmt)
                insert_idx += 1
                
        file_obj.write_text('\n'.join(lines), encoding='utf-8')
        print(f"✓ {file_path}: Fixed imports")

def fix_indentation_errors():
    """Fix indentation errors in specific files"""
    
    # Fix check_environment.py
    check_env = Path("check_environment.py")
    if check_env.exists():
        content = check_env.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Fix indentation issues around line 26
        for i, line in enumerate(lines):
            if line.strip().startswith('try:') and 'import' in lines[i+1]:
                # Fix indentation of the import block
                j = i + 1
                while j < len(lines) and (lines[j].strip().startswith('import') or lines[j].strip().startswith('except') or lines[j].strip() == '' or '= None' in lines[j]):
                    if lines[j].strip():
                        # Ensure proper indentation
                        if lines[j].strip().startswith('import'):
                            lines[j] = '    ' + lines[j].strip()
                        elif lines[j].strip().startswith('except'):
                            lines[j] = lines[j].strip()
                        elif '= None' in lines[j]:
                            lines[j] = '    ' + lines[j].strip()
                    j += 1
                break
                
        check_env.write_text('\n'.join(lines), encoding='utf-8')
        print("✓ check_environment.py: Fixed indentation")
    
    # Fix test_celery_integration.py
    celery_test = Path("test_celery_integration.py")
    if celery_test.exists():
        content = celery_test.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Fix any indentation issues
        fixed_lines = []
        for line in lines:
            if line.strip():
                # Remove any excessive indentation
                stripped = line.lstrip()
                if stripped.startswith('import') or stripped.startswith('from'):
                    fixed_lines.append(stripped)
                else:
                    # Maintain reasonable indentation for other lines
                    indent_level = (len(line) - len(line.lstrip())) // 4
                    if indent_level > 0:
                        fixed_lines.append('    ' * min(indent_level, 4) + stripped)
                    else:
                        fixed_lines.append(stripped)
            else:
                fixed_lines.append('')
                
        celery_test.write_text('\n'.join(fixed_lines), encoding='utf-8')
        print("✓ test_celery_integration.py: Fixed indentation")

if __name__ == "__main__":
    print("🔧 Fixing syntax errors and missing imports...")
    
    fix_adapter_imports()
    fix_typing_imports()
    fix_test_files()
    fix_indentation_errors()
    
    print("✅ Syntax fixes completed!")
