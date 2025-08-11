#!/usr/bin/env python3
"""
Script to fix null bytes in files by recreating them
"""
from pathlib import Path

def fix_file(filepath):
    """Remove null bytes from file by recreating it"""
    try:
        # Read content as text (this will fail if there are encoding issues)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Remove null bytes and other problematic characters
        clean_content = content.replace('\x00', '').strip()
        
        # Write back the clean content
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(clean_content)
        
        print(f"✓ Fixed: {filepath}")
        return True
        
    except Exception as e:
        print(f"✗ Error fixing {filepath}: {e}")
        return False

def main():
    base_dir = Path(__file__).parent
    
    # List of problematic files found by debug script
    problematic_files = [
        'production_patch.py',
        'converter/api_views.py',
        'converter/views.py', 
        'converter/views_comprehensive.py',
        'converter_site/railway_settings.py'
    ]
    
    print("Fixing null bytes in files...")
    print("=" * 40)
    
    for file_path in problematic_files:
        full_path = base_dir / file_path
        if full_path.exists():
            fix_file(full_path)
        else:
            print(f"✗ File not found: {file_path}")
    
    print("\nDone! Run debug_deployment.py again to verify.")

if __name__ == "__main__":
    main()
