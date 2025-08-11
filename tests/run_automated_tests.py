#!/usr/bin/env python3
"""
Automated Test Runner for Step 6: Form validation and integration tests.

This script runs all automated tests including:
- Unit tests: form validation edge cases (too big, wrong format, invalid times)
- Integration tests: client posts small sample mp4, asserts 200 and gif content-type
- Uses pytest, django assertions, and sample fixtures under tests/media/

Usage:
    python tests/run_automated_tests.py
    python tests/run_automated_tests.py --unit-only
    python tests/run_automated_tests.py --integration-only
    python tests/run_automated_tests.py --verbose
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
import django
django.setup()

def run_pytest_tests(test_pattern=None, verbose=False, collect_only=False):
    """Run pytest with specified pattern and options"""
    
    cmd = ['python', '-m', 'pytest']
    
    if verbose:
        cmd.extend(['-v', '-s'])
    
    if collect_only:
        cmd.append('--collect-only')
    
    # Add test directory
    test_dir = Path(__file__).parent
    
    if test_pattern:
        cmd.append(str(test_dir / test_pattern))
    else:
        # Run all test files
        cmd.extend([
            str(test_dir / 'test_form_validation.py'),
            str(test_dir / 'test_integration_mp4_to_gif.py')
        ])
    
    # Add pytest options for better output
    cmd.extend([
        '--tb=short',  # Shorter traceback format
        '--strict-markers',  # Strict marker handling
        '-x'  # Stop on first failure
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n\nTest run interrupted by user.")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def check_test_fixtures():
    """Verify that test fixtures (sample media files) exist"""
    media_dir = Path(__file__).parent / 'media'
    
    required_files = [
        'small_sample.mp4',
        'medium_sample.mp4',
        'wrong_format.txt',
        'invalid_times.json'
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = media_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        print("❌ Missing test fixture files:")
        for file_name in missing_files:
            print(f"   - tests/media/{file_name}")
        print("\nRun 'python tests/create_test_media.py' to create them.")
        return False
    
    print("✅ All test fixture files are present")
    return True

def run_unit_tests(verbose=False):
    """Run unit tests only"""
    print("🧪 Running Unit Tests (Form Validation Edge Cases)")
    print("-" * 60)
    return run_pytest_tests('test_form_validation.py', verbose=verbose)

def run_integration_tests(verbose=False):
    """Run integration tests only"""
    print("🔗 Running Integration Tests (MP4 to GIF Conversion)")
    print("-" * 60)
    return run_pytest_tests('test_integration_mp4_to_gif.py', verbose=verbose)

def run_all_tests(verbose=False):
    """Run all automated tests"""
    print("🚀 Running All Automated Tests")
    print("=" * 80)
    
    # Check fixtures first
    if not check_test_fixtures():
        print("\n❌ Cannot run tests without fixture files.")
        return 1
    
    print("\n📋 Test Summary:")
    print("   - Unit tests: Form validation edge cases")
    print("   - Integration tests: Client MP4 upload → GIF response")
    print("   - Framework: pytest + Django assertions")
    print("   - Fixtures: tests/media/ sample files")
    print()
    
    return run_pytest_tests(verbose=verbose)

def collect_test_info():
    """Collect and display information about available tests"""
    print("📊 Collecting Test Information...")
    print("=" * 80)
    return run_pytest_tests(collect_only=True, verbose=True)

def main():
    parser = argparse.ArgumentParser(
        description="Run automated tests for form validation and MP4 to GIF conversion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_automated_tests.py                    # Run all tests
  python tests/run_automated_tests.py --unit-only       # Unit tests only
  python tests/run_automated_tests.py --integration-only # Integration tests only  
  python tests/run_automated_tests.py --verbose         # Verbose output
  python tests/run_automated_tests.py --collect         # Show available tests
        """
    )
    
    parser.add_argument('--unit-only', action='store_true',
                       help='Run unit tests only (form validation)')
    parser.add_argument('--integration-only', action='store_true', 
                       help='Run integration tests only (MP4 to GIF)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--collect', action='store_true',
                       help='Collect and show test information only')
    
    args = parser.parse_args()
    
    if args.collect:
        return collect_test_info()
    elif args.unit_only and args.integration_only:
        print("❌ Cannot specify both --unit-only and --integration-only")
        return 1
    elif args.unit_only:
        return run_unit_tests(verbose=args.verbose)
    elif args.integration_only:
        return run_integration_tests(verbose=args.verbose)
    else:
        return run_all_tests(verbose=args.verbose)

if __name__ == '__main__':
    sys.exit(main())
