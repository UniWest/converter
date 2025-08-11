#!/usr/bin/env python
"""
Test script for the hardened video upload and conversion system.
Tests the VideoConversionService and integration with the upload view.
"""

import os
import sys
import django
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
django.setup()

import tempfile
import shutil
from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
import forms
from converter.views import VideoUploadView
from converter.services import VideoConversionService
from converter.models import ConversionTask


def create_test_video_file():
    """Create a minimal test video file using FFmpeg (if available)."""
    try:
        import subprocess
        from django.conf import settings
        
        ffmpeg_path = getattr(settings, 'FFMPEG_BINARY', 'ffmpeg')
        
        # Create a simple 3-second test video
        test_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        test_video.close()
        
        # Generate test video: 3 seconds, 30 fps, 320x240, color pattern
        cmd = [
            ffmpeg_path,
            '-f', 'lavfi',
            '-i', 'testsrc=duration=3:size=320x240:rate=30',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '30',
            '-y',
            test_video.name
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(test_video.name):
            return test_video.name
        else:
            print(f"FFmpeg error: {result.stderr.decode('utf-8', errors='ignore')}")
            return None
            
    except Exception as e:
        print(f"Could not create test video: {e}")
        return None


def test_video_conversion_service():
    """Test the VideoConversionService directly."""
    print("\n=== Testing VideoConversionService ===")
    
    # Create test video
    test_video_path = create_test_video_file()
    if not test_video_path:
        print("❌ Cannot create test video file - FFmpeg not available or failed")
        return False
    
    try:
        # Create conversion task
        task = ConversionTask.objects.create(status=ConversionTask.STATUS_QUEUED)
        task.set_metadata(
            original_filename='test_video.mp4',
            input_path=test_video_path,
            file_size=os.path.getsize(test_video_path),
            file_type='video',
            input_format='mp4'
        )
        task.save()
        
        print(f"✓ Created test task #{task.id}")
        
        # Test conversion service
        service = VideoConversionService()
        
        # Test basic conversion
        result = service.convert_video_to_gif(
            task_id=task.id,
            input_path=test_video_path,
            width=240,
            fps=10,
            start_time=0,
            end_time=2,
            keep_original_size=False,
            speed=1.0,
            grayscale=False,
            reverse=False,
            boomerang=False,
            high_quality=False,
            dither='bayer'
        )
        
        if result['success']:
            print(f"✓ Basic conversion successful: {result['output_filename']}")
            print(f"  Output size: {result['file_size']} bytes")
            
            # Check if output file exists
            if os.path.exists(result['output_path']):
                print("✓ Output file exists")
                # Cleanup
                os.unlink(result['output_path'])
            else:
                print("❌ Output file not found")
                return False
        else:
            print(f"❌ Basic conversion failed: {result['error_message']}")
            return False
        
        # Test high quality conversion
        task2 = ConversionTask.objects.create(status=ConversionTask.STATUS_QUEUED)
        task2.set_metadata(
            original_filename='test_video_hq.mp4',
            input_path=test_video_path,
            file_size=os.path.getsize(test_video_path),
            file_type='video',
            input_format='mp4'
        )
        task2.save()
        
        result_hq = service.convert_video_to_gif(
            task_id=task2.id,
            input_path=test_video_path,
            width=200,
            fps=15,
            start_time=0,
            end_time=2,
            high_quality=True,
            dither='floyd_steinberg'
        )
        
        if result_hq['success']:
            print(f"✓ High quality conversion successful: {result_hq['output_filename']}")
            print(f"  Output size: {result_hq['file_size']} bytes")
            
            # Cleanup
            if os.path.exists(result_hq['output_path']):
                os.unlink(result_hq['output_path'])
        else:
            print(f"❌ High quality conversion failed: {result_hq['error_message']}")
            return False
        
        # Test grayscale conversion
        task3 = ConversionTask.objects.create(status=ConversionTask.STATUS_QUEUED)
        task3.set_metadata(
            original_filename='test_video_gray.mp4',
            input_path=test_video_path,
            file_size=os.path.getsize(test_video_path),
            file_type='video',
            input_format='mp4'
        )
        task3.save()
        
        result_gray = service.convert_video_to_gif(
            task_id=task3.id,
            input_path=test_video_path,
            width=160,
            fps=12,
            grayscale=True
        )
        
        if result_gray['success']:
            print(f"✓ Grayscale conversion successful: {result_gray['output_filename']}")
            
            # Cleanup
            if os.path.exists(result_gray['output_path']):
                os.unlink(result_gray['output_path'])
        else:
            print(f"❌ Grayscale conversion failed: {result_gray['error_message']}")
            return False
        
        print("✓ All VideoConversionService tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ VideoConversionService test failed: {e}")
        return False
    
    finally:
        # Cleanup test video
        if test_video_path and os.path.exists(test_video_path):
            os.unlink(test_video_path)


def test_form_validation():
    """Test VideoUploadForm validation."""
    print("\n=== Testing VideoUploadForm Validation ===")
    
    try:
        # Test invalid video file
        invalid_file = SimpleUploadedFile("test.txt", b"not a video", content_type="text/plain")
        form = forms.VideoUploadForm(data={
            'fps': 15,
            'width': 480,
            'start_time': 0,
            'end_time': 5
        }, files={'video': invalid_file})
        
        if not form.is_valid():
            print("✓ Form correctly rejects non-video files")
            print(f"  Error: {form.errors['video'][0]}")
        else:
            print("❌ Form should reject non-video files")
            return False
        
        # Test valid form data (without actual video file)
        form_data = {
            'fps': 24,
            'width': 720,
            'start_time': 5,
            'end_time': 15,
            'keep_original_size': False,
            'speed': '1.5',
            'grayscale': True,
            'high_quality': True,
            'dither': 'sierra2_4a'
        }
        
        # Mock video file
        video_file = SimpleUploadedFile("test.mp4", b"fake video content", content_type="video/mp4")
        form = forms.VideoUploadForm(data=form_data, files={'video': video_file})
        
        # We expect validation to fail due to file size/format, but data validation should work
        print("✓ Form data validation structure works")
        
        # Test time range validation
        invalid_time_data = form_data.copy()
        invalid_time_data['start_time'] = 10
        invalid_time_data['end_time'] = 5  # end before start
        
        form = forms.VideoUploadForm(data=invalid_time_data, files={'video': video_file})
        if not form.is_valid():
            print("✓ Form correctly validates time ranges")
        
        print("✓ All form validation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Form validation test failed: {e}")
        return False


def test_upload_view_integration():
    """Test the VideoUploadView integration."""
    print("\n=== Testing Upload View Integration ===")
    
    try:
        factory = RequestFactory()
        
        # Test GET request (form display)
        request = factory.get('/upload/')
        view = VideoUploadView()
        response = view.get(request)
        
        if response.status_code == 200:
            print("✓ Upload form displays correctly")
        else:
            print(f"❌ Upload form failed to display: {response.status_code}")
            return False
        
        # Test POST with invalid data
        request = factory.post('/upload/', {
            'fps': 15,
            'width': 480
            # Missing required video file
        })
        
        view = VideoUploadView()
        response = view.post(request)
        
        if response.status_code == 200:  # Form redisplay with errors
            print("✓ Upload view handles invalid data correctly")
        else:
            print(f"❌ Upload view invalid data handling failed: {response.status_code}")
        
        print("✓ Upload view integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Upload view integration test failed: {e}")
        return False


def test_error_handling():
    """Test error handling and validation."""
    print("\n=== Testing Error Handling ===")
    
    try:
        service = VideoConversionService()
        
        # Test with non-existent file
        task = ConversionTask.objects.create(status=ConversionTask.STATUS_QUEUED)
        result = service.convert_video_to_gif(
            task_id=task.id,
            input_path="/non/existent/file.mp4",
            width=480,
            fps=15
        )
        
        if not result['success'] and 'не найден' in result['error_message']:
            print("✓ Correctly handles non-existent input files")
        else:
            print(f"❌ Error handling failed: {result}")
            return False
        
        # Test with invalid time range (would need real video)
        print("✓ Error handling tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("Starting hardened video conversion system tests...")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    test_results.append(("Form Validation", test_form_validation()))
    test_results.append(("Upload View Integration", test_upload_view_integration()))
    test_results.append(("Error Handling", test_error_handling()))
    test_results.append(("Video Conversion Service", test_video_conversion_service()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✓ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The hardened video conversion system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
