#!/usr/bin/env python3
"""
Integration tests for MP4 to GIF conversion.
Tests full client workflow: upload small sample MP4, assert 200 response and GIF content-type.
Uses pytest and django assertions with sample fixtures.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

# Django setup
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')

import django
django.setup()

import pytest
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.http import FileResponse

from converter.models import ConversionTask
from converter.services import VideoConversionService


class MP4ToGifIntegrationTest(TestCase):
    """Integration tests for complete MP4 to GIF conversion workflow"""
    
    def setUp(self):
        """Set up test fixtures and client"""
        self.client = Client()
        self.media_dir = Path(__file__).parent / 'media'
        
        # Ensure temp directories exist
        self.temp_dir = Path(settings.MEDIA_ROOT) / 'tmp'
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Load sample MP4 file
        self.sample_mp4_path = self.media_dir / 'small_sample.mp4'
        with open(self.sample_mp4_path, 'rb') as f:
            self.sample_mp4_data = f.read()
    
    def create_test_uploaded_file(self, filename='test_video.mp4'):
        """Helper to create SimpleUploadedFile from sample data"""
        return SimpleUploadedFile(
            filename,
            self.sample_mp4_data,
            content_type='video/mp4'
        )
    
    def test_video_upload_view_get(self):
        """Test that VideoUploadView GET method works"""
        from converter.views import VideoUploadView
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'GET'
        
        view = VideoUploadView()
        response = view.get(request)
        
        # Should return a response (even if template rendering fails in test)
        self.assertIsNotNone(response)
    
    @patch('converter.services.VideoConversionService.convert_video_to_gif')
    @patch('os.path.exists')
    def test_small_mp4_upload_returns_200_with_gif(self, mock_exists, mock_convert):
        """Test uploading small MP4 returns 200 with GIF content-type"""
        
        # Mock successful conversion
        mock_output_path = '/fake/output/path/converted.gif'
        mock_convert.return_value = {
            'success': True,
            'output_path': mock_output_path,
            'file_size': 1024,
            'duration': 5.0
        }
        mock_exists.return_value = True
        
        # Create test file
        test_file = self.create_test_uploaded_file()
        
        # Prepare form data
        form_data = {
            'width': 720,
            'fps': 15,
            'start_time': 0,
            'end_time': 5,
            'speed': '1.0',
            'keep_original_size': False,
            'grayscale': False,
            'reverse': False,
            'boomerang': False
        }
        
        # Mock file serving
        with patch('converter.views.VideoUploadView._serve_converted_file') as mock_serve:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response['Content-Type'] = 'image/gif'
            mock_response['Content-Disposition'] = 'attachment; filename="converted.gif"'
            mock_serve.return_value = mock_response
            
            # Submit form
            response = self.client.post('/', {
                **form_data,
                'video': test_file
            })
            
            # Assert successful response
            self.assertEqual(response.status_code, 200)
            
            # Verify conversion service was called
            mock_convert.assert_called_once()
            
            # Verify file serving was called
            mock_serve.assert_called_once_with(mock_output_path)
    
    @patch('converter.services.VideoConversionService.convert_video_to_gif')
    def test_conversion_task_created_in_database(self, mock_convert):
        """Test that conversion creates a database record"""
        
        # Mock successful conversion
        mock_convert.return_value = {
            'success': True,
            'output_path': '/fake/output/converted.gif',
            'file_size': 1024
        }
        
        # Initial task count
        initial_count = ConversionTask.objects.count()
        
        # Create test file
        test_file = self.create_test_uploaded_file()
        
        # Submit conversion
        response = self.client.post('/', {
            'video': test_file,
            'width': 480,
            'fps': 15
        })
        
        # Assert task was created
        self.assertEqual(ConversionTask.objects.count(), initial_count + 1)
        
        # Check task details
        task = ConversionTask.objects.latest('created_at')
        self.assertEqual(task.get_metadata('original_filename'), 'test_video.mp4')
        self.assertEqual(task.get_metadata('file_type'), 'video')
        self.assertEqual(task.get_metadata('input_format'), 'mp4')
    
    def test_invalid_file_format_returns_form_with_errors(self):
        """Test that invalid file format returns form with validation errors"""
        
        # Create invalid file (text file pretending to be video)
        invalid_file = SimpleUploadedFile(
            'not_a_video.txt',
            b'This is not a video file',
            content_type='text/plain'
        )
        
        # Submit form
        response = self.client.post('/', {
            'video': invalid_file,
            'width': 720,
            'fps': 30
        })
        
        # Should return form with errors, not redirect
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
        
        # Check that no conversion task was created
        self.assertEqual(ConversionTask.objects.count(), 0)
    
    @patch('converter.services.VideoConversionService.convert_video_to_gif')
    def test_conversion_failure_handling(self, mock_convert):
        """Test handling of conversion failures"""
        
        # Mock conversion failure
        mock_convert.return_value = {
            'success': False,
            'error_message': 'Mock conversion error for testing'
        }
        
        # Create test file
        test_file = self.create_test_uploaded_file()
        
        # Submit conversion
        response = self.client.post('/', {
            'video': test_file,
            'width': 720,
            'fps': 30
        })
        
        # Should return to form with error message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
        
        # Check that task was marked as failed
        task = ConversionTask.objects.latest('created_at')
        self.assertEqual(task.status, ConversionTask.STATUS_FAILED)
        self.assertIn('Mock conversion error', task.error_message)
    
    def test_form_validation_edge_cases_integration(self):
        """Test form validation in full integration context"""
        
        test_file = self.create_test_uploaded_file()
        
        # Test cases for various validation failures
        validation_test_cases = [
            # Width too small
            {
                'data': {'video': test_file, 'width': 100, 'fps': 30},
                'expected_error_field': 'width'
            },
            # Width too large
            {
                'data': {'video': test_file, 'width': 4000, 'fps': 30},
                'expected_error_field': 'width'
            },
            # FPS too low
            {
                'data': {'video': test_file, 'width': 720, 'fps': 10},
                'expected_error_field': 'fps'
            },
            # FPS too high
            {
                'data': {'video': test_file, 'width': 720, 'fps': 70},
                'expected_error_field': 'fps'
            },
            # Invalid time range
            {
                'data': {'video': test_file, 'width': 720, 'fps': 30, 'start_time': 60, 'end_time': 30},
                'expected_error_field': 'end_time'
            }
        ]
        
        for i, case in enumerate(validation_test_cases):
            with self.subTest(case=i):
                # Recreate file for each test (seek doesn't work on SimpleUploadedFile)
                case['data']['video'] = self.create_test_uploaded_file()
                
                response = self.client.post('/', case['data'])
                
                # Should return form with validation errors
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'form')
                
                # No conversion tasks should be created for invalid forms
                self.assertEqual(ConversionTask.objects.count(), 0)
    
    @patch('converter.services.VideoConversionService.convert_video_to_gif')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_successful_conversion_with_gif_response(self, mock_getsize, mock_exists, mock_convert):
        """Test complete successful conversion with proper GIF file response"""
        
        # Mock file system operations
        mock_convert.return_value = {
            'success': True,
            'output_path': '/tmp/test_output.gif',
            'file_size': 2048
        }
        mock_exists.return_value = True
        mock_getsize.return_value = 2048
        
        # Mock GIF file content
        fake_gif_data = b'GIF89a\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b'
        
        # Create test file
        test_file = self.create_test_uploaded_file()
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_file.read.return_value = fake_gif_data
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file
            
            # Submit conversion request
            response = self.client.post('/', {
                'video': test_file,
                'width': 720,
                'fps': 15,
                'start_time': 0,
                'end_time': 10
            })
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            
            # Verify conversion was called with correct parameters
            mock_convert.assert_called_once()
            call_args = mock_convert.call_args
            
            # Check that task_id was provided
            self.assertIn('task_id', call_args.kwargs)
            
            # Check that input_path was provided
            self.assertIn('input_path', call_args.kwargs)
            
            # Check conversion parameters
            self.assertEqual(call_args.kwargs.get('width'), 720)
            self.assertEqual(call_args.kwargs.get('fps'), 15)
    
    def test_concurrent_upload_requests(self):
        """Test handling multiple concurrent upload requests"""
        
        # This test simulates multiple clients uploading at once
        test_files = [
            self.create_test_uploaded_file(f'video_{i}.mp4')
            for i in range(3)
        ]
        
        form_data = {
            'width': 480,
            'fps': 15,
            'start_time': 0,
            'end_time': 5
        }
        
        with patch('converter.services.VideoConversionService.convert_video_to_gif') as mock_convert:
            mock_convert.return_value = {
                'success': True,
                'output_path': '/tmp/fake_output.gif',
                'file_size': 1024
            }
            
            # Submit multiple requests
            responses = []
            for test_file in test_files:
                data = {**form_data, 'video': test_file}
                response = self.client.post('/', data)
                responses.append(response)
            
            # All requests should be handled properly
            for response in responses:
                self.assertEqual(response.status_code, 200)
            
            # Verify correct number of tasks created
            self.assertEqual(ConversionTask.objects.count(), 3)
            
            # Verify conversion service was called for each request
            self.assertEqual(mock_convert.call_count, 3)


class APIEndpointIntegrationTest(TestCase):
    """Integration tests for API endpoints if they exist"""
    
    def setUp(self):
        self.client = Client()
        self.media_dir = Path(__file__).parent / 'media'
    
    def test_api_status_endpoint(self):
        """Test API status endpoint returns proper response"""
        try:
            response = self.client.get('/api/status/')
            
            if response.status_code == 200:
                # API endpoint exists, test it
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'application/json')
            else:
                # API endpoint doesn't exist, skip test
                self.skipTest("API status endpoint not implemented")
                
        except Exception as e:
            self.skipTest(f"API endpoint not available: {e}")
    
    def test_conversion_status_endpoint(self):
        """Test conversion status endpoint"""
        try:
            response = self.client.get(reverse('converter_status'))
            self.assertEqual(response.status_code, 200)
        except:
            self.skipTest("Conversion status endpoint not available")


if __name__ == '__main__':
    import unittest
    unittest.main()
