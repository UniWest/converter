#!/usr/bin/env python
import tempfile
from unittest.mock import Mock, patch
"""
Интеграционные тесты для конвертера видео в GIF.
Эти тесты проверяют работу системы в целом и взаимодействие компонентов.

Для запуска тестов:
python manage.py test test_integration
"""

import os
import shutil
from django.test import TestCase, override_settings
from django.test.client import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings

from converter.utils import VideoConverter, save_uploaded_video, save_converted_gif, cleanup_temp_files
import forms


class VideoConverterIntegrationTests(TestCase):
    """Интеграционные тесты для системы конвертации видео"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.client = Client()
        
        # Создаем временную директорию для медиафайлов
        self.temp_media_root = tempfile.mkdtemp()
        
        # Создаем тестовый видеофайл (имитируем)
        self.test_video_content = b'FAKE_MP4_CONTENT_FOR_TESTING' * 1000  # ~27KB
        self.test_video_file = SimpleUploadedFile(
            "test_integration_video.mp4",
            self.test_video_content,
            content_type="video/mp4"
        )
    
    def tearDown(self):
        """Очистка после тестов"""
        # Удаляем временную директорию
        if os.path.exists(self.temp_media_root):
            shutil.rmtree(self.temp_media_root)
    
    @override_settings(MEDIA_ROOT='/tmp/test_integration_media')
    @patch('converter.utils.VideoConverter._convert_with_moviepy')
    @patch('converter.utils.VideoConverter.get_video_info')
    def test_full_conversion_workflow_moviepy(self, mock_get_info, mock_convert):
        """Тест полного процесса конвертации с использованием MoviePy"""
        # Настраиваем моки
        mock_get_info.return_value = {
            'duration': 60.0,
            'width': 1920,
            'height': 1080,
            'fps': 30.0,
            'codec': 'h264',
            'bitrate': 1000000
        }
        
        def mock_convert_side_effect(video_file, output_path, **kwargs):
            # Имитируем создание GIF файла
            with open(output_path, 'wb') as f:
                f.write(b'FAKE_GIF_CONTENT')
            return True
        
        mock_convert.side_effect = mock_convert_side_effect
        
        # Создаем конвертер
        converter = VideoConverter(use_moviepy=True)
        
        # Создаем временный файл для вывода
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_output:
            output_path = temp_output.name
        
        try:
            # Выполняем конвертацию
            result = converter.convert_video_to_gif(
                self.test_video_file,
                output_path,
                width=480,
                fps=15,
                start_time=0,
                end_time=30
            )
            
            # Проверяем результат
            self.assertTrue(result)
            self.assertTrue(os.path.exists(output_path))
            
            # Проверяем, что файл не пустой
            with open(output_path, 'rb') as f:
                content = f.read()
                self.assertGreater(len(content), 0)
            
            # Проверяем, что методы были вызваны
            mock_convert.assert_called_once()
            
        finally:
            # Очищаем временные файлы
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    @override_settings(MEDIA_ROOT='/tmp/test_integration_media')
    @patch('converter.utils.subprocess.run')
    def test_full_conversion_workflow_ffmpeg(self, mock_subprocess):
        """Тест полного процесса конвертации с использованием FFmpeg"""
        # Настраиваем мок subprocess
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            if 'ffmpeg' in cmd[0] and '-version' in cmd:
                # Имитируем проверку версии FFmpeg
                result = Mock()
                result.returncode = 0
                return result
            elif 'ffmpeg' in cmd[0]:
                # Имитируем конвертацию
                # Ищем выходной файл в команде
                output_file = cmd[-1]
                if output_file.endswith('.gif'):
                    with open(output_file, 'wb') as f:
                        f.write(b'FAKE_GIF_CONTENT_FROM_FFMPEG')
                
                result = Mock()
                result.returncode = 0
                result.stderr = ""
                return result
            
            result = Mock()
            result.returncode = 1
            return result
        
        mock_subprocess.side_effect = mock_run_side_effect
        
        # Создаем конвертер с FFmpeg
        converter = VideoConverter(use_moviepy=False)
        
        # Создаем временный файл для вывода
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_output:
            output_path = temp_output.name
        
        try:
            # Выполняем конвертацию
            result = converter.convert_video_to_gif(
                self.test_video_file,
                output_path,
                width=480,
                fps=15
            )
            
            # Проверяем результат
            self.assertTrue(result)
            self.assertTrue(os.path.exists(output_path))
            
            # Проверяем содержимое файла
            with open(output_path, 'rb') as f:
                content = f.read()
                self.assertEqual(content, b'FAKE_GIF_CONTENT_FROM_FFMPEG')
            
        finally:
            # Очищаем временные файлы
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    @override_settings(MEDIA_ROOT='/tmp/test_integration_media', MEDIA_URL='/media/')
    def test_upload_and_save_workflow(self):
        """Тест процесса загрузки и сохранения файлов"""
        
        # Создаем тестовые директории
        upload_dir = os.path.join('/tmp/test_integration_media', 'uploads', 'videos')
        gif_dir = os.path.join('/tmp/test_integration_media', 'gifs')
        
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(gif_dir, exist_ok=True)
        
        try:
            # Тестируем сохранение загруженного видео
            video_path = save_uploaded_video(self.test_video_file)
            self.assertIsNotNone(video_path)
            self.assertTrue(os.path.exists(video_path))
            
            # Проверяем содержимое сохраненного файла
            with open(video_path, 'rb') as f:
                saved_content = f.read()
                self.assertEqual(saved_content, self.test_video_content)
            
            # Создаем временный GIF файл
            with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_gif:
                temp_gif.write(b'FAKE_GIF_DATA_FOR_TEST')
                temp_gif_path = temp_gif.name
            
            # Тестируем сохранение конвертированного GIF
            gif_url = save_converted_gif(temp_gif_path, 'test_video.mp4')
            self.assertIsNotNone(gif_url)
            self.assertTrue(gif_url.startswith('/media/gifs/'))
            self.assertTrue(gif_url.endswith('.gif'))
            
            # Проверяем, что GIF файл существует
            gif_filename = os.path.basename(gif_url.replace('/media/', ''))
            gif_full_path = os.path.join('/tmp/test_integration_media', 'gifs', gif_filename)
            self.assertTrue(os.path.exists(gif_full_path))
            
            # Тестируем очистку временных файлов
            temp_files = [video_path]
            cleanup_temp_files(temp_files)
            self.assertFalse(os.path.exists(video_path))
            
        finally:
            # Очищаем созданные файлы
            if 'video_path' in locals() and os.path.exists(video_path):
                os.unlink(video_path)
            if 'temp_gif_path' in locals() and os.path.exists(temp_gif_path):
                os.unlink(temp_gif_path)
            if 'gif_full_path' in locals() and os.path.exists(gif_full_path):
                os.unlink(gif_full_path)
    
    def test_form_validation_integration(self):
        """Тест интеграции валидации форм"""
        
        # Тестируем валидную форму
        valid_form_data = {
            'width': 1280,
            'fps': 24,
            'start_time': 0,
            'end_time': 60
        }
        
        form = forms.VideoUploadForm(
            data=valid_form_data,
            files={'video': self.test_video_file}
        )
        
        self.assertTrue(form.is_valid())
        
        # Получаем настройки конвертации
        settings_data = form.get_conversion_settings()
        self.assertIsNotNone(settings_data)
        self.assertEqual(settings_data['width'], 1280)
        self.assertEqual(settings_data['fps'], 24)
        self.assertEqual(settings_data['start_time'], 0)
        self.assertEqual(settings_data['end_time'], 60)
        
        # Тестируем форму быстрой обработки
        processing_form_data = {
            'quality': '720p'
        }
        
        processing_form = forms.VideoProcessingForm(
            data=processing_form_data,
            files={'video': self.test_video_file}
        )
        
        self.assertTrue(processing_form.is_valid())
        
        quality_settings = processing_form.get_quality_settings()
        self.assertEqual(quality_settings['width'], 1280)
        self.assertEqual(quality_settings['height'], 720)
        self.assertEqual(quality_settings['fps'], 30)
    
    @patch('converter.views.VideoConverter')
    @patch('converter.views.save_converted_gif')
    def test_ajax_conversion_integration(self, mock_save_gif, mock_converter_class):
        """Тест интеграции AJAX конвертации"""
        
        # Настраиваем моки
        mock_converter = Mock()
        mock_converter_class.return_value = mock_converter
        mock_converter.convert_video_to_gif.return_value = True
        mock_converter.get_video_info.return_value = {
            'duration': 120.0,
            'width': 1920,
            'height': 1080,
            'fps': 30.0
        }
        
        mock_save_gif.return_value = '/media/gifs/test_converted.gif'
        
        # Отправляем AJAX запрос
        response = self.client.post(
            reverse('ajax_convert'),
            {
                'video': self.test_video_file,
                'width': '640',
                'fps': '20',
                'start_time': '5',
                'end_time': '65'
            }
        )
        
        # Проверяем ответ
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        import json
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['gif_url'], '/media/gifs/test_converted.gif')
        self.assertIn('video_info', response_data)
        self.assertIn('message', response_data)
        
        # Проверяем, что конвертер был вызван с правильными параметрами
        mock_converter.convert_video_to_gif.assert_called_once()
        call_args = mock_converter.convert_video_to_gif.call_args
        
        # Проверяем параметры конвертации
        self.assertEqual(call_args.kwargs['width'], 640)
        self.assertEqual(call_args.kwargs['fps'], 20)
        self.assertEqual(call_args.kwargs['start_time'], 5)
        self.assertEqual(call_args.kwargs['end_time'], 65)
    
    @patch('converter.views.VideoConverter')
    def test_video_info_integration(self, mock_converter_class):
        """Тест интеграции получения информации о видео"""
        
        # Настраиваем мок
        mock_converter = Mock()
        mock_converter_class.return_value = mock_converter
        mock_converter.get_video_info.return_value = {
            'duration': 240.5,
            'width': 1920,
            'height': 1080,
            'fps': 25.0,
            'codec': 'h264',
            'bitrate': 5000000
        }
        
        # Отправляем запрос на получение информации о видео
        response = self.client.post(
            reverse('video_info'),
            {'video': self.test_video_file}
        )
        
        # Проверяем ответ
        self.assertEqual(response.status_code, 200)
        
        import json
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertIn('info', response_data)
        
        info = response_data['info']
        self.assertEqual(info['duration'], 240.5)
        self.assertEqual(info['width'], 1920)
        self.assertEqual(info['height'], 1080)
        self.assertEqual(info['fps'], 25.0)
        self.assertEqual(info['codec'], 'h264')
        self.assertEqual(info['bitrate'], 5000000)
    
    def test_converter_status_integration(self):
        """Тест интеграции проверки статуса конвертера"""
        
        with patch('converter.views.VideoConverter') as mock_converter_class:
            # Настраиваем мок
            mock_converter = Mock()
            mock_converter_class.return_value = mock_converter
            mock_converter._check_ffmpeg.return_value = True
            
            response = self.client.get(reverse('converter_status'))
            
            self.assertEqual(response.status_code, 200)
            
            import json
            response_data = json.loads(response.content)
            
            self.assertIn('moviepy_available', response_data)
            self.assertIn('ffmpeg_available', response_data)
            self.assertIn('ffmpeg_path', response_data)
            self.assertIn('recommended_engine', response_data)
    
    def test_error_handling_integration(self):
        """Тест интеграции обработки ошибок"""
        
        # Тест с невалидным файлом
        invalid_file = SimpleUploadedFile(
            "test.txt",
            b"This is not a video file",
            content_type="text/plain"
        )
        
        # Тест AJAX конвертации с невалидным файлом
        response = self.client.post(
            reverse('ajax_convert'),
            {
                'video': invalid_file,
                'width': '480',
                'fps': '15'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Тест без файла
        response = self.client.post(
            reverse('ajax_convert'),
            {'width': '480', 'fps': '15'}
        )
        
        self.assertEqual(response.status_code, 200)
        
        import json
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)


if __name__ == '__main__':
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["test_integration"])
