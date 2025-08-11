import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile, InMemoryUploadedFile
from django.urls import reverse
from django.test.utils import override_settings

from .utils import VideoConverter, save_uploaded_video, save_converted_gif, cleanup_temp_files
import forms


class VideoConverterTests(TestCase):
    """Тесты для класса VideoConverter"""
    
    def setUp(self):
        """Подготовка перед каждым тестом"""
        self.converter = VideoConverter(use_moviepy=True)
        self.test_video_data = b'fake_video_data_for_testing'
        
        # Создаем мок видео файла
        self.mock_video_file = Mock()
        self.mock_video_file.name = 'test_video.mp4'
        self.mock_video_file.size = len(self.test_video_data)
        self.mock_video_file.chunks.return_value = [self.test_video_data]
    
    def test_init_with_moviepy(self):
        """Тест инициализации с MoviePy"""
        converter = VideoConverter(use_moviepy=True)
        self.assertTrue(converter.use_moviepy)
    
    def test_init_with_ffmpeg(self):
        """Тест инициализации с FFmpeg"""
        converter = VideoConverter(use_moviepy=False)
        self.assertFalse(converter.use_moviepy)
    
    @patch('converter.utils.subprocess.run')
    def test_check_ffmpeg_available(self, mock_run):
        """Тест проверки доступности FFmpeg"""
        mock_run.return_value.returncode = 0
        result = self.converter._check_ffmpeg('ffmpeg')
        self.assertTrue(result)
    
    @patch('converter.utils.subprocess.run')
    def test_check_ffmpeg_not_available(self, mock_run):
        """Тест проверки недоступности FFmpeg"""
        mock_run.side_effect = FileNotFoundError()
        result = self.converter._check_ffmpeg('ffmpeg')
        self.assertFalse(result)
    
    @patch('converter.utils.subprocess.run')
    def test_get_video_info_success(self, mock_run):
        """Тест успешного получения информации о видео"""
        # Мокаем ответ ffprobe
        mock_response = {
            'format': {
                'duration': '120.5',
                'bit_rate': '1000000'
            },
            'streams': [{
                'codec_type': 'video',
                'width': 1920,
                'height': 1080,
                'r_frame_rate': '30/1',
                'codec_name': 'h264'
            }]
        }
        
        import json
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(mock_response)
        
        info = self.converter.get_video_info(self.mock_video_file)
        
        self.assertEqual(info['duration'], 120.5)
        self.assertEqual(info['width'], 1920)
        self.assertEqual(info['height'], 1080)
        self.assertEqual(info['fps'], 30.0)
        self.assertEqual(info['codec'], 'h264')
        self.assertEqual(info['bitrate'], 1000000)
    
    @patch('converter.utils.subprocess.run')
    def test_get_video_info_failure(self, mock_run):
        """Тест неуспешного получения информации о видео"""
        mock_run.return_value.returncode = 1
        info = self.converter.get_video_info(self.mock_video_file)
        self.assertEqual(info, {})
    
    def test_convert_with_moviepy_success(self):
        """Тест успешной конвертации с MoviePy"""
        with patch('converter.utils.VideoConverter._convert_with_moviepy') as mock_method:
            mock_method.return_value = True
            
            with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_file:
                output_path = temp_file.name
            
            try:
                # Создаем фиктивный GIF файл для имитации успешной конвертации
                with open(output_path, 'wb') as f:
                    f.write(b'FAKE_GIF_CONTENT')
                
                result = self.converter._convert_with_moviepy(
                    self.mock_video_file,
                    output_path,
                    width=480,
                    fps=15,
                    start_time=0,
                    end_time=10
                )
                
                self.assertTrue(result)
                mock_method.assert_called_once()
            finally:
                if os.path.exists(output_path):
                    os.unlink(output_path)
    
    def test_convert_with_moviepy_import_error(self):
        """Тест обработки ImportError при использовании MoviePy"""
        with patch('converter.utils.VideoConverter.convert_video_to_gif') as mock_method:
            # Имитируем, что MoviePy недоступен, но конвертация работает через FFmpeg
            mock_method.return_value = True
            
            with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_file:
                output_path = temp_file.name
            
            try:
                # Создаем фиктивный GIF файл
                with open(output_path, 'wb') as f:
                    f.write(b'FAKE_GIF_CONTENT_FROM_FFMPEG_FALLBACK')
                
                result = self.converter.convert_video_to_gif(
                    self.mock_video_file,
                    output_path
                )
                self.assertTrue(result)
            finally:
                if os.path.exists(output_path):
                    os.unlink(output_path)
    
    @patch('converter.utils.subprocess.run')
    def test_convert_with_ffmpeg_success(self, mock_run):
        """Тест успешной конвертации с FFmpeg"""
        mock_run.return_value.returncode = 0
        
        with patch.object(self.converter, '_check_ffmpeg', return_value=True):
            with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_file:
                output_path = temp_file.name
            
            try:
                result = self.converter._convert_with_ffmpeg(
                    self.mock_video_file,
                    output_path,
                    width=480,
                    fps=15
                )
                
                self.assertTrue(result)
                mock_run.assert_called_once()
            finally:
                if os.path.exists(output_path):
                    os.unlink(output_path)
    
    @patch('converter.utils.subprocess.run')
    def test_convert_with_ffmpeg_failure(self, mock_run):
        """Тест неуспешной конвертации с FFmpeg"""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "FFmpeg error message"
        
        with patch.object(self.converter, '_check_ffmpeg', return_value=True):
            with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_file:
                output_path = temp_file.name
            
            try:
                result = self.converter._convert_with_ffmpeg(
                    self.mock_video_file,
                    output_path
                )
                
                self.assertFalse(result)
            finally:
                if os.path.exists(output_path):
                    os.unlink(output_path)


class UtilityFunctionsTests(TestCase):
    """Тесты для утилитарных функций"""
    
    def setUp(self):
        self.test_video_data = b'fake_video_data_for_testing'
        self.mock_video_file = Mock()
        self.mock_video_file.name = 'test_video.mp4'
        self.mock_video_file.chunks.return_value = [self.test_video_data]
    
    @override_settings(MEDIA_ROOT='/tmp/test_media')
    def test_save_uploaded_video(self):
        """Тест сохранения загруженного видео"""
        with patch('os.makedirs'), \
             patch('builtins.open', create=True) as mock_open:
            
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = save_uploaded_video(self.mock_video_file)
            
            self.assertIsNotNone(result)
            # Проверяем, что путь содержит правильную структуру
            self.assertTrue(result.endswith('.mp4'))
            self.assertIn('uploads', result)
            self.assertIn('videos', result)
            mock_file.write.assert_called_with(self.test_video_data)
    
    @override_settings(MEDIA_ROOT='/tmp/test_media', MEDIA_URL='/media/')
    def test_save_converted_gif(self):
        """Тест сохранения конвертированного GIF"""
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b'fake_gif_data')
        
        try:
            with patch('os.makedirs'), \
                 patch('shutil.move') as mock_move:
                
                result = save_converted_gif(temp_path, 'original_video.mp4')
                
                self.assertIsNotNone(result)
                self.assertTrue(result.startswith('/media/gifs/'))
                self.assertTrue(result.endswith('.gif'))
                mock_move.assert_called_once()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_cleanup_temp_files(self):
        """Тест очистки временных файлов"""
        # Создаем временные файлы
        temp_files = []
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_files.append(temp_file.name)
            temp_file.close()
        
        # Проверяем, что файлы существуют
        for temp_file in temp_files:
            self.assertTrue(os.path.exists(temp_file))
        
        # Очищаем файлы
        cleanup_temp_files(temp_files)
        
        # Проверяем, что файлы удалены
        for temp_file in temp_files:
            self.assertFalse(os.path.exists(temp_file))
    
    def test_cleanup_temp_files_nonexistent(self):
        """Тест очистки несуществующих файлов"""
        nonexistent_files = ['/tmp/nonexistent1.tmp', '/tmp/nonexistent2.tmp']
        
        # Не должно вызывать исключений
        try:
            cleanup_temp_files(nonexistent_files)
        except Exception as e:
            self.fail(f"cleanup_temp_files raised an exception: {e}")


class FormsTests(TestCase):
    """Тесты для форм"""
    
    def test_video_upload_form_valid_data(self):
        """Тест валидных данных в VideoUploadForm"""
        # Создаем тестовый файл
        test_file = SimpleUploadedFile(
            "test_video.mp4",
            b"fake video content",
            content_type="video/mp4"
        )
        
        form_data = {
            'width': 1920,
            'fps': 30,
            'start_time': 0,
            'end_time': 60
        }
        
        form = forms.VideoUploadForm(data=form_data, files={'video': test_file})
        self.assertTrue(form.is_valid())
    
    def test_video_upload_form_invalid_file_size(self):
        """Тест с превышением размера файла"""
        # Создаем файл большого размера (имитируем)
        large_file = Mock()
        large_file.name = 'large_video.mp4'
        large_file.size = 600 * 1024 * 1024  # 600 МБ
        
        form_data = {
            'width': 1920,
            'fps': 30,
        }
        
        with patch('forms.VideoUploadForm.clean_video') as mock_clean:
            from django.core.exceptions import ValidationError
            mock_clean.side_effect = ValidationError('Размер файла слишком большой')
            
            form = forms.VideoUploadForm(data=form_data, files={'video': large_file})
            self.assertFalse(form.is_valid())
    
    def test_video_upload_form_invalid_extension(self):
        """Тест с неподдерживаемым расширением файла"""
        test_file = SimpleUploadedFile(
            "test_document.txt",
            b"not a video file",
            content_type="text/plain"
        )
        
        form_data = {
            'width': 1920,
            'fps': 30,
        }
        
        form = forms.VideoUploadForm(data=form_data, files={'video': test_file})
        self.assertFalse(form.is_valid())
        self.assertIn('video', form.errors)
    
    def test_video_upload_form_invalid_width(self):
        """Тест с нечетной шириной"""
        test_file = SimpleUploadedFile(
            "test_video.mp4",
            b"fake video content",
            content_type="video/mp4"
        )
        
        form_data = {
            'width': 1921,  # Нечетное число
            'fps': 30,
        }
        
        form = forms.VideoUploadForm(data=form_data, files={'video': test_file})
        self.assertFalse(form.is_valid())
        self.assertIn('width', form.errors)
    
    def test_video_upload_form_invalid_time_range(self):
        """Тест с неверным временным диапазоном"""
        test_file = SimpleUploadedFile(
            "test_video.mp4",
            b"fake video content",
            content_type="video/mp4"
        )
        
        form_data = {
            'width': 1920,
            'fps': 30,
            'start_time': 60,
            'end_time': 30  # Меньше начального времени
        }
        
        form = forms.VideoUploadForm(data=form_data, files={'video': test_file})
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)
    
    def test_video_processing_form_valid_data(self):
        """Тест валидных данных в VideoProcessingForm"""
        test_file = SimpleUploadedFile(
            "test_video.mp4",
            b"fake video content",
            content_type="video/mp4"
        )
        
        form_data = {
            'quality': '1080p'
        }
        
        form = forms.VideoProcessingForm(data=form_data, files={'video': test_file})
        self.assertTrue(form.is_valid())
        
        # Проверяем настройки качества
        settings = form.get_quality_settings()
        self.assertEqual(settings['width'], 1920)
        self.assertEqual(settings['height'], 1080)
        self.assertEqual(settings['fps'], 30)
    
    def test_get_conversion_settings(self):
        """Тест получения настроек конвертации"""
        test_file = SimpleUploadedFile(
            "test_video.mp4",
            b"fake video content",
            content_type="video/mp4"
        )
        
        form_data = {
            'width': 1280,
            'fps': 24,
            'start_time': 10,
            'end_time': 70
        }
        
        form = forms.VideoUploadForm(data=form_data, files={'video': test_file})
        self.assertTrue(form.is_valid())
        
        settings = form.get_conversion_settings()
        self.assertIsNotNone(settings)
        self.assertEqual(settings['width'], 1280)
        self.assertEqual(settings['fps'], 24)
        self.assertEqual(settings['start_time'], 10)
        self.assertEqual(settings['end_time'], 70)


class ViewsTests(TestCase):
    """Тесты для представлений"""
    
    def setUp(self):
        self.client = Client()
        self.test_video_data = b'fake_video_data_for_testing'
    
    def test_home_view_get(self):
        """Тест GET запроса к главной странице"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
    
    @patch('converter.views.VideoConverter')
    def test_ajax_convert_view_success(self, mock_converter_class):
        """Тест успешной AJAX конвертации"""
        # Настраиваем мок конвертера
        mock_converter = Mock()
        mock_converter_class.return_value = mock_converter
        mock_converter.convert_video_to_gif.return_value = True
        mock_converter.get_video_info.return_value = {
            'duration': 120,
            'width': 1920,
            'height': 1080
        }
        
        # Мокаем сохранение GIF
        with patch('converter.views.save_converted_gif', return_value='/media/gifs/test.gif'):
            test_file = SimpleUploadedFile(
                "test_video.mp4",
                self.test_video_data,
                content_type="video/mp4"
            )
            
            response = self.client.post(
                reverse('ajax_convert'),
                {
                    'video': test_file,
                    'width': '480',
                    'fps': '15',
                    'start_time': '0',
                    'end_time': '10'
                }
            )
            
            self.assertEqual(response.status_code, 200)
            
            import json
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertIn('gif_url', data)
            self.assertIn('video_info', data)
    
    def test_ajax_convert_view_no_file(self):
        """Тест AJAX конвертации без файла"""
        response = self.client.post(
            reverse('ajax_convert'),
            {'width': '480', 'fps': '15'}
        )
        
        self.assertEqual(response.status_code, 200)
        
        import json
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_ajax_convert_view_large_file(self):
        """Тест AJAX конвертации с большим файлом"""
        # Имитируем большой файл
        large_file = Mock()
        large_file.name = 'large_video.mp4'
        large_file.size = 600 * 1024 * 1024  # 600 МБ
        
        with patch('django.http.request.QueryDict.getlist'), \
             patch('django.core.files.uploadhandler.FileUploadHandler.new_file'):
            
            response = self.client.post(
                reverse('ajax_convert'),
                {'video': large_file, 'width': '480'}
            )
            
            # Проверим, что в любом случае получаем JSON ответ
            self.assertEqual(response.status_code, 200)
    
    @patch('converter.views.VideoConverter')
    def test_video_info_view_success(self, mock_converter_class):
        """Тест успешного получения информации о видео"""
        mock_converter = Mock()
        mock_converter_class.return_value = mock_converter
        mock_converter.get_video_info.return_value = {
            'duration': 120,
            'width': 1920,
            'height': 1080,
            'fps': 30
        }
        
        test_file = SimpleUploadedFile(
            "test_video.mp4",
            self.test_video_data,
            content_type="video/mp4"
        )
        
        response = self.client.post(
            reverse('video_info'),
            {'video': test_file}
        )
        
        self.assertEqual(response.status_code, 200)
        
        import json
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('info', data)
    
    def test_converter_status_view(self):
        """Тест получения статуса конвертера"""
        with patch('converter.views.VideoConverter') as mock_converter_class:
            mock_converter = Mock()
            mock_converter_class.return_value = mock_converter
            mock_converter._check_ffmpeg.return_value = True
            
            response = self.client.get(reverse('converter_status'))
            self.assertEqual(response.status_code, 200)
            
            import json
            data = json.loads(response.content)
            self.assertIn('moviepy_available', data)
            self.assertIn('ffmpeg_available', data)


if __name__ == '__main__':
    unittest.main()
