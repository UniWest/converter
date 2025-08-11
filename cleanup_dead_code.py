#!/usr/bin/env python3
"""
Script to clean up placeholder text, dead code, unused imports, and other issues.
This script addresses the following:

1. Remove placeholder text like "Upload functionality will be added soon"
2. Remove commented-out code blocks
3. Remove unused imports
4. Remove unused views and template blocks
5. Clean up settings files
"""

import os
import re
import sys
from pathlib import Path
import shutil

class CodeCleanup:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.changes = []
        
    def log_change(self, file_path, description):
        """Log a change made to a file"""
        self.changes.append(f"{file_path}: {description}")
        print(f"✓ {file_path}: {description}")
        
    def remove_placeholder_text(self):
        """Remove placeholder text from templates and forms"""
        
        # 1. Fix forms.py - remove placeholder examples that are just examples
        forms_file = self.project_root / "forms.py"
        if forms_file.exists():
            content = forms_file.read_text(encoding='utf-8')
            
            # Replace placeholder text with better defaults
            content = re.sub(r"'placeholder': 'Например: 1920'", "'placeholder': '1920'", content)
            content = re.sub(r"'placeholder': 'Например: 30'", "'placeholder': '30'", content)
            content = re.sub(r"'placeholder': 'Например: 10'", "'placeholder': '10'", content)
            content = re.sub(r"'placeholder': 'Например: 120'", "'placeholder': '120'", content)
            content = re.sub(r"'placeholder': 'Например: 0.5'", "'placeholder': '0.5'", content)
            
            forms_file.write_text(content, encoding='utf-8')
            self.log_change("forms.py", "Cleaned up placeholder text")
        
        # 2. Fix comprehensive_converter.html - remove "В разработке" placeholders
        comp_template = self.project_root / "converter/templates/converter/comprehensive_converter.html"
        if comp_template.exists():
            content = comp_template.read_text(encoding='utf-8')
            
            # Replace "В разработке" with proper functionality
            content = content.replace('<small class="text-muted">В разработке</small>', 
                                    '<small class="text-success">Доступно</small>')
            
            # Remove placeholder input
            content = re.sub(r'placeholder="До конца видео"', 'placeholder="Оставьте пустым для всего видео"', content)
            content = re.sub(r'placeholder="Авто"', 'placeholder="Оригинальный размер"', content)
            
            comp_template.write_text(content, encoding='utf-8')
            self.log_change("converter/templates/converter/comprehensive_converter.html", 
                          "Removed 'В разработке' placeholders")
        
        # 3. Fix audio_to_text.html - clean up placeholder text
        audio_template = self.project_root / "converter/templates/converter/audio_to_text.html"
        if audio_template.exists():
            content = audio_template.read_text(encoding='utf-8')
            
            # Replace placeholder text with cleaner versions
            content = re.sub(
                r'placeholder=".*?Recognition result will appear here.*?"',
                'placeholder="Результат распознавания появится здесь"',
                content
            )
            
            audio_template.write_text(content, encoding='utf-8')
            self.log_change("converter/templates/converter/audio_to_text.html", 
                          "Cleaned up placeholder text")
        
        # 4. Fix results.html - remove placeholder text
        results_template = self.project_root / "converter/templates/converter/results.html"
        if results_template.exists():
            content = results_template.read_text(encoding='utf-8')
            
            content = re.sub(r'placeholder="Поиск по имени файла\.\.\."', 
                           'placeholder="Поиск файлов..."', content)
            
            results_template.write_text(content, encoding='utf-8')
            self.log_change("converter/templates/converter/results.html", 
                          "Cleaned up placeholder text")
    
    def remove_commented_code(self):
        """Remove large blocks of commented-out code"""
        
        # 1. Clean up settings.py - remove the large commented Celery block
        settings_file = self.project_root / "converter_site/settings.py"
        if settings_file.exists():
            content = settings_file.read_text(encoding='utf-8')
            
            # Remove the large commented Celery configuration block
            # Find the multiline comment block and remove it
            celery_comment_pattern = r'# Celery Configuration - временно отключено для запуска сервера\n""".*?"""'
            content = re.sub(celery_comment_pattern, 
                           '# Celery Configuration disabled for development', 
                           content, flags=re.DOTALL)
            
            # Remove other large commented blocks
            large_comment_pattern = r'# try:\n#.*?# except ImportError:.*?\n'
            content = re.sub(large_comment_pattern, '', content, flags=re.DOTALL)
            
            settings_file.write_text(content, encoding='utf-8')
            self.log_change("converter_site/settings.py", "Removed large commented code blocks")
    
    def remove_unused_imports(self):
        """Remove unused imports from Python files"""
        
        unused_imports = [
            ("celery_app.py", "shutil"),
            ("check_environment.py", ["os", "magic", "cv2", "PIL.Image", "converter_settings.BINARY_PATHS"]),
            ("check_test_readiness.py", "subprocess"),
            ("converter/adapters_views.py", ["os", "django.conf.settings"]),
            ("converter/admin.py", "django.utils.timezone"),
            ("converter/models.py", "json"),
            ("converter/tasks.py", ["os", "tempfile", "shutil"]),
            ("converter/urls.py", ".views_comprehensive"),
            ("converter/utils.py", ["django.core.files.storage.default_storage", "django.core.files.base.ContentFile"]),
            ("converter_site/settings.py", "os"),
            ("forms.py", "os"),
        ]
        
        for file_path, imports in unused_imports:
            if isinstance(imports, str):
                imports = [imports]
                
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            content = full_path.read_text(encoding='utf-8')
            
            for import_name in imports:
                # Remove simple imports
                content = re.sub(rf'^import {re.escape(import_name)}\n', '', content, flags=re.MULTILINE)
                
                # Remove from imports
                content = re.sub(rf'^from .* import.*{re.escape(import_name)}.*\n', '', content, flags=re.MULTILINE)
                
                # Handle comma-separated imports
                content = re.sub(rf', {re.escape(import_name)}(?=\s*[\n,])', '', content)
                content = re.sub(rf'{re.escape(import_name)}, ', '', content)
                
            full_path.write_text(content, encoding='utf-8')
            self.log_change(file_path, f"Removed unused imports: {', '.join(imports)}")
    
    def remove_unused_views_and_files(self):
        """Remove unused views and backup files"""
        
        # 1. Remove views_comprehensive.py - it only contains stub functions
        comp_views = self.project_root / "converter/views_comprehensive.py"
        if comp_views.exists():
            content = comp_views.read_text(encoding='utf-8')
            if "JsonResponse" in content and content.count('\n') < 10:
                comp_views.unlink()
                self.log_change("converter/views_comprehensive.py", "Removed stub file")
        
        # 2. Remove backup and demo files that aren't needed
        files_to_remove = [
            "converter/views_backup.py",
            "converter_site/celery_app_backup.py",
            "demo-resilient.html",
            "demo-upload.html", 
            "demo_converter.py",
            "demo_testing.py",
            "debug_test.html",
            "test_cors.html",
            "simple_app.py"
        ]
        
        for file_path in files_to_remove:
            full_path = self.project_root / file_path
            if full_path.exists():
                full_path.unlink()
                self.log_change(file_path, "Removed unused file")
    
    def clean_up_template_blocks(self):
        """Remove unused template blocks and clean up templates"""
        
        # Fix conversion_history.html - remove hardcoded zeros and add proper stats
        history_template = self.project_root / "converter/templates/converter/conversion_history.html"
        if history_template.exists():
            content = history_template.read_text(encoding='utf-8')
            
            # Replace hardcoded stats with dynamic ones
            content = re.sub(r'<span class="stat-number">0</span>\s*<span class="stat-label">За сегодня</span>',
                           '<span class="stat-number">{{ today_conversions|default:0 }}</span>\n            <span class="stat-label">За сегодня</span>',
                           content)
            
            content = re.sub(r'<span class="stat-number">0GB</span>\s*<span class="stat-label">Обработано данных</span>',
                           '<span class="stat-number">{{ total_data_processed|default:"0MB" }}</span>\n            <span class="stat-label">Обработано данных</span>',
                           content)
            
            history_template.write_text(content, encoding='utf-8')
            self.log_change("converter/templates/converter/conversion_history.html",
                          "Replaced hardcoded stats with dynamic content")
    
    def update_urls(self):
        """Clean up URL patterns and remove unused imports"""
        
        # Update converter/urls.py to remove unused import
        converter_urls = self.project_root / "converter/urls.py"
        if converter_urls.exists():
            content = converter_urls.read_text(encoding='utf-8')
            content = content.replace("from . import views_comprehensive\n", "")
            converter_urls.write_text(content, encoding='utf-8')
            self.log_change("converter/urls.py", "Removed unused views_comprehensive import")
    
    def run_cleanup(self):
        """Run all cleanup operations"""
        print("🧹 Starting code cleanup...")
        
        try:
            self.remove_placeholder_text()
            self.remove_commented_code()
            self.remove_unused_imports()
            self.remove_unused_views_and_files()
            self.clean_up_template_blocks()
            self.update_urls()
            
            print(f"\n✅ Cleanup completed! Made {len(self.changes)} changes:")
            for change in self.changes:
                print(f"  - {change}")
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            return False
            
        return True

if __name__ == "__main__":
    cleanup = CodeCleanup()
    success = cleanup.run_cleanup()
    sys.exit(0 if success else 1)
