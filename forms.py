from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.forms.widgets import FileInput
import os


class MultipleFileInput(FileInput):
    """Кастомный виджет для загрузки множественных файлов."""
    
    allow_multiple_selected = True
    
    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs['multiple'] = True
        super().__init__(attrs)
    
    def value_from_datadict(self, data, files, name):
        upload = files.getlist(name)
        if not upload:
            return None
        return upload


class VideoUploadForm(forms.Form):
    """
    Форма для загрузки и конвертации видео.
    
    Содержит поля:
    - video: загружаемый видеофайл
    - width: ширина выходного видео
    - fps: частота кадров
    - start_time: начальное время обрезки (в секундах)
    - end_time: конечное время обрезки (в секундах)
    """
    
    # Поле для загрузки видеофайла
    video = forms.FileField(
        label='Видеофайл',
        help_text='Выберите видеофайл для конвертации (поддерживаемые форматы: mp4, avi, mov, mkv, wmv)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/*'
        })
    )
    
    # Опция для сохранения оригинальных размеров
    keep_original_size = forms.BooleanField(
        label='Сохранить оригинальные размеры видео',
        help_text='Если отмечено, видео будет конвертировано с оригинальными размерами',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'keep_original_size'
        })
    )
    
    # Поле для ширины видео
    width = forms.IntegerField(
        label='Ширина (пиксели)',
        help_text='Ширина выходного видео в пикселях (от 144 до 3840)',
        validators=[
            MinValueValidator(144, message='Минимальная ширина должна быть не менее 144 пикселей'),
            MaxValueValidator(3840, message='Максимальная ширина не должна превышать 3840 пикселей (4K)')
        ],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 144,
            'max': 3840,
            'step': 1,
            'placeholder': 'Например: 1920',
            'id': 'width_input'
        }),
        initial=720,  # Снижаем для скорости
        required=False
    )
    
    # Поле для частоты кадров
    fps = forms.IntegerField(
        label='FPS (кадров в секунду)',
        help_text='Частота кадров выходного видео (от 15 до 60 fps)',
        validators=[
            MinValueValidator(15, message='FPS должен быть не менее 15'),
            MaxValueValidator(60, message='FPS не должен превышать 60')
        ],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 15,
            'max': 60,
            'step': 1,
            'placeholder': 'Например: 30'
        }),
        initial=15  # Снижаем FPS для скорости
    )

    # Скорость воспроизведения
    SPEED_CHOICES = [
        (0.5, '0.5x (медленнее)'),
        (1.0, '1x (нормальная)'),
        (1.5, '1.5x (быстрее)'),
        (2.0, '2x (быстрее)')
    ]
    speed = forms.ChoiceField(
        label='Скорость воспроизведения',
        choices=[(str(k), v) for k, v in SPEED_CHOICES],
        initial='1.0',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Эффекты
    grayscale = forms.BooleanField(
        label='Монохром (черно-белый)',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    reverse = forms.BooleanField(
        label='Реверс (воспроизведение назад)',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    boomerang = forms.BooleanField(
        label='Бумеранг (туда-обратно)',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # Качество цвета GIF
    high_quality = forms.BooleanField(
        label='Высокое качество цветов (медленнее)',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    DITHER_CHOICES = [
        ('bayer', 'Bayer (по умолчанию)'),
        ('sierra2_4a', 'Sierra 2-4A (мягкий)'),
        ('floyd_steinberg', 'Floyd-Steinberg (резкий)'),
        ('none', 'Без дизеринга')
    ]
    dither = forms.ChoiceField(
        label='Тип дизеринга (для высокого качества)',
        choices=DITHER_CHOICES,
        initial='bayer',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Поле для начального времени обрезки
    start_time = forms.IntegerField(
        label='Начальное время (секунды)',
        help_text='Время начала фрагмента в секундах (0 - начало видео)',
        validators=[
            MinValueValidator(0, message='Время начала не может быть отрицательным')
        ],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'step': 1,
            'placeholder': 'Например: 10'
        }),
        initial=0,
        required=False
    )
    
    # Поле для конечного времени обрезки
    end_time = forms.IntegerField(
        label='Конечное время (секунды)',
        help_text='Время окончания фрагмента в секундах (оставьте пустым для всего видео)',
        validators=[
            MinValueValidator(1, message='Время окончания должно быть больше 0')
        ],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'step': 1,
            'placeholder': 'Например: 120'
        }),
        required=False
    )

    def clean_video(self):
        """
        Валидация загружаемого видеофайла.
        Проверяет размер файла и формат.
        """
        video = self.cleaned_data.get('video')
        
        if video:
            # Проверяем размер файла (максимум 500 МБ)
            max_size = 500 * 1024 * 1024  # 500 МБ в байтах
            if video.size > max_size:
                raise ValidationError(
                    f'Размер файла слишком большой. Максимальный размер: 500 МБ. '
                    f'Размер загруженного файла: {video.size / (1024*1024):.1f} МБ'
                )
            
            # Проверяем расширение файла
            allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
            file_name = video.name.lower()
            
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise ValidationError(
                    f'Неподдерживаемый формат файла. '
                    f'Разрешенные форматы: {", ".join(allowed_extensions)}'
                )
        
        return video

    def clean_width(self):
        """
        Дополнительная валидация ширины видео.
        """
        width = self.cleaned_data.get('width')
        
        if width:
            # Проверяем, что ширина кратна 2 (требование FFmpeg для некоторых кодеков)
            if width % 2 != 0:
                raise ValidationError('Ширина видео должна быть четным числом')
        
        return width

    def clean_fps(self):
        """
        Дополнительная валидация FPS.
        """
        fps = self.cleaned_data.get('fps')
        
        if fps:
            # Список наиболее распространенных значений FPS
            common_fps = [15, 24, 25, 30, 48, 50, 60]
            
            if fps not in common_fps:
                # Предупреждение, но не ошибка
                pass
        
        return fps

    def clean(self):
        """
        Общая валидация формы.
        Проверяет логическую связность всех полей.
        """
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Проверяем, что время окончания больше времени начала
        if start_time is not None and end_time is not None:
            if end_time <= start_time:
                raise ValidationError({
                    'end_time': 'Время окончания должно быть больше времени начала'
                })
            
            # Проверяем, что продолжительность фрагмента не меньше 1 секунды
            duration = end_time - start_time
            if duration < 1:
                raise ValidationError({
                    'end_time': 'Минимальная продолжительность фрагмента должна быть 1 секунда'
                })
            
            # Проверяем, что продолжительность не превышает 10 минут (600 секунд)
            max_duration = 600  # 10 минут
            if duration > max_duration:
                raise ValidationError({
                    'end_time': f'Максимальная продолжительность фрагмента: {max_duration} секунд (10 минут)'
                })
        
        return cleaned_data

    def get_conversion_settings(self):
        """
        Возвращает словарь с настройками для конвертации.
        Используется для передачи параметров в процесс конвертации.
        """
        if not self.is_valid():
            return None
            
        settings = {
            'video_file': self.cleaned_data['video'],
            'width': self.cleaned_data.get('width'),
            'fps': self.cleaned_data['fps'],
            'start_time': self.cleaned_data.get('start_time', 0),
            'end_time': self.cleaned_data.get('end_time'),
            'keep_original_size': self.cleaned_data.get('keep_original_size', False),
            'speed': float(self.cleaned_data.get('speed') or 1.0),
            'grayscale': self.cleaned_data.get('grayscale', False),
            'reverse': self.cleaned_data.get('reverse', False),
            'boomerang': self.cleaned_data.get('boomerang', False),
            'high_quality': self.cleaned_data.get('high_quality', False),
            'dither': self.cleaned_data.get('dither') or 'bayer',
        }
        
        return settings


class VideoProcessingForm(forms.Form):
    """
    Упрощенная форма для быстрых настроек конвертации видео.
    Содержит только основные параметры с предустановленными значениями.
    """
    
    video = forms.FileField(
        label='Видеофайл',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/*'
        })
    )
    
    # Предустановленные варианты качества
    QUALITY_CHOICES = [
        ('720p', 'HD (1280x720, 30 fps)'),
        ('1080p', 'Full HD (1920x1080, 30 fps)'),
        ('480p', 'SD (854x480, 24 fps)'),
        ('custom', 'Пользовательские настройки'),
    ]
    
    quality = forms.ChoiceField(
        choices=QUALITY_CHOICES,
        label='Качество видео',
        initial='1080p',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    def clean_video(self):
        """Базовая валидация видеофайла."""
        video = self.cleaned_data.get('video')
        
        if video and video.size > 200 * 1024 * 1024:  # 200 МБ для быстрой обработки
            raise ValidationError('Для быстрой обработки размер файла не должен превышать 200 МБ')
        
        return video
    
    def get_quality_settings(self):
        """Возвращает настройки качества в зависимости от выбранного варианта."""
        quality = self.cleaned_data.get('quality')
        
        quality_map = {
            '720p': {'width': 1280, 'height': 720, 'fps': 30},
            '1080p': {'width': 1920, 'height': 1080, 'fps': 30},
            '480p': {'width': 854, 'height': 480, 'fps': 24},
        }
        
        return quality_map.get(quality, {})


class AudioToTextForm(forms.Form):
    """
    Форма для конвертации аудио в текст (Speech-to-Text).
    Поддерживает различные аудио форматы и языки.
    """
    
    # Поле для загрузки аудиофайла
    audio = forms.FileField(
        label='Аудиофайл',
        help_text='Выберите аудиофайл для распознавания речи (mp3, wav, m4a, flac, ogg)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'audio/*,.mp3,.wav,.m4a,.flac,.ogg'
        })
    )
    
    # Язык распознавания
    LANGUAGE_CHOICES = [
        ('ru-RU', 'Русский'),
        ('en-US', 'English (US)'),
        ('en-GB', 'English (UK)'),
        ('es-ES', 'Español'),
        ('fr-FR', 'Français'),
        ('de-DE', 'Deutsch'),
        ('it-IT', 'Italiano'),
        ('pt-BR', 'Português (Brasil)'),
        ('zh-CN', '中文 (简体)'),
        ('ja-JP', '日本語'),
        ('ko-KR', '한국어'),
    ]
    
    language = forms.ChoiceField(
        label='Язык распознавания',
        choices=LANGUAGE_CHOICES,
        initial='ru-RU',
        help_text='Выберите язык, на котором произносится речь в аудио',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Качество распознавания
    QUALITY_CHOICES = [
        ('fast', 'Быстрое (меньшая точность)'),
        ('standard', 'Обычное (сбалансированное)'),
        ('high', 'Высокое (лучшая точность, медленнее)'),
    ]
    
    quality = forms.ChoiceField(
        label='Качество распознавания',
        choices=QUALITY_CHOICES,
        initial='standard',
        help_text='Высокое качество даёт лучшие результаты, но занимает больше времени',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Формат вывода
    OUTPUT_FORMAT_CHOICES = [
        ('txt', 'Простой текст (.txt)'),
        ('srt', 'Субтитры (.srt)'),
        ('json', 'JSON с временными метками'),
    ]
    
    output_format = forms.ChoiceField(
        label='Формат результата',
        choices=OUTPUT_FORMAT_CHOICES,
        initial='txt',
        help_text='Формат файла с распознанным текстом',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Опции для дополнительной обработки
    enhance_speech = forms.BooleanField(
        label='Улучшить качество звука',
        help_text='Подавление шума и усиление речи (замедляет обработку)',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    remove_silence = forms.BooleanField(
        label='Удалить тишину',
        help_text='Автоматически удалять длинные паузы в аудио',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_audio(self):
        """Валидация загружаемого аудиофайла."""
        audio = self.cleaned_data.get('audio')
        
        if audio:
            # Проверяем размер файла (максимум 200 МБ)
            max_size = 200 * 1024 * 1024  # 200 МБ в байтах
            if audio.size > max_size:
                raise ValidationError(
                    f'Размер файла слишком большой. Максимальный размер: 200 МБ. '
                    f'Размер загруженного файла: {audio.size / (1024*1024):.1f} МБ'
                )
            
            # Проверяем расширение файла
            allowed_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma']
            file_name = audio.name.lower()
            
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise ValidationError(
                    f'Неподдерживаемый формат файла. '
                    f'Разрешенные форматы: {", ".join(allowed_extensions)}'
                )
        
        return audio


class ImagesToGifForm(forms.Form):
    """
    Форма для создания GIF анимации из набора изображений.
    Поддерживает загрузку нескольких изображений и создание анимации.
    """
    
    # Поле для загрузки нескольких изображений
    images = forms.FileField(
        label='Изображения',
        help_text='Выберите несколько изображений для создания GIF анимации (JPG, PNG, WebP)',
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.jpg,.jpeg,.png,.webp,.bmp'
        })
    )
    
    # Продолжительность кадра
    frame_duration = forms.FloatField(
        label='Продолжительность кадра (секунды)',
        help_text='Как долго каждое изображение будет показываться (от 0.1 до 5.0 секунд)',
        validators=[
            MinValueValidator(0.1, message='Минимальная продолжительность кадра: 0.1 секунды'),
            MaxValueValidator(5.0, message='Максимальная продолжительность кадра: 5.0 секунд')
        ],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0.1,
            'max': 5.0,
            'step': 0.1,
            'placeholder': 'Например: 0.5'
        }),
        initial=0.5
    )
    
    # Размер выходного GIF
    SIZE_CHOICES = [
        ('original', 'Оригинальный размер'),
        ('320', '320px (маленькие)'),
        ('480', '480px (средние)'),
        ('720', '720px (большие)'),
        ('1080', '1080px (очень большие)'),
    ]
    
    output_size = forms.ChoiceField(
        label='Размер GIF',
        choices=SIZE_CHOICES,
        initial='480',
        help_text='Размер выходного GIF. Меньший размер = меньший размер файла',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Качество цветов
    COLOR_CHOICES = [
        ('256', '256 цветов (максимальное качество)'),
        ('128', '128 цветов (высокое)'),
        ('64', '64 цвета (среднее)'),
        ('32', '32 цвета (низкое, маленькие файлы)'),
    ]
    
    colors = forms.ChoiceField(
        label='Количество цветов',
        choices=COLOR_CHOICES,
        initial='128',
        help_text='Больше цветов = лучше качество, но больше размер файла',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Опции лупа
    loop = forms.BooleanField(
        label='Луп (бесконечное воспроизведение)',
        help_text='GIF будет воспроизводиться в кольце бесконечно',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Порядок сортировки
    ORDER_CHOICES = [
        ('filename', 'По имени файла'),
        ('upload', 'По порядку загрузки'),
        ('reverse', 'Обратный порядок'),
    ]
    
    sort_order = forms.ChoiceField(
        label='Порядок кадров',
        choices=ORDER_CHOICES,
        initial='filename',
        help_text='Как упорядочить изображения в анимации',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Эффекты
    pingpong = forms.BooleanField(
        label='Пинг-понг (туда-обратно)',
        help_text='Анимация будет воспроизводиться вперёд, а затем назад',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    optimize = forms.BooleanField(
        label='Оптимизация размера',
        help_text='Уменьшает размер файла за счёт оптимизации',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_images(self):
        """Валидация загружаемых изображений."""
        images = self.files.getlist('images')
        
        if not images:
            raise ValidationError('Необходимо загрузить хотя бы одно изображение')
        
        if len(images) < 2:
            raise ValidationError('Для создания GIF нужно минимум 2 изображения')
        
        if len(images) > 100:
            raise ValidationError('Максимум 100 изображений за раз')
        
        total_size = 0
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
        
        for image in images:
            # Проверяем размер каждого файла (максимум 10 МБ)
            max_single_size = 10 * 1024 * 1024  # 10 МБ
            if image.size > max_single_size:
                raise ValidationError(
                    f'Размер файла {image.name} слишком большой. '
                    f'Максимум 10 МБ на файл'
                )
            
            # Проверяем расширение
            file_name = image.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise ValidationError(
                    f'Неподдерживаемый формат файла {image.name}. '
                    f'Разрешенные форматы: {", ".join(allowed_extensions)}'
                )
            
            total_size += image.size
        
        # Проверяем общий размер (максимум 100 МБ)
        max_total_size = 100 * 1024 * 1024  # 100 МБ
        if total_size > max_total_size:
            raise ValidationError(
                f'Общий размер всех файлов слишком большой. '
                f'Максимум 100 МБ в сумме. '
                f'Текущий размер: {total_size / (1024*1024):.1f} МБ'
            )
        
        return images
