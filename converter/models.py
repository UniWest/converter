from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json


class ConversionTask(models.Model):
    """Модель для отслеживания задач конвертации файлов"""
    
    # Статусы задач
    STATUS_QUEUED = 'queued'
    STATUS_RUNNING = 'running'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'В очереди'),
        (STATUS_RUNNING, 'Выполняется'),
        (STATUS_DONE, 'Завершено'),
        (STATUS_FAILED, 'Ошибка'),
    ]
    
    # Основные поля
    id = models.AutoField(primary_key=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
        verbose_name='Статус'
    )
    
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Прогресс (%)',
        help_text='Прогресс выполнения от 0 до 100'
    )
    
    # Метаданные задачи
    task_metadata = models.JSONField(
        default=dict,
        verbose_name='Метаданные задачи',
        help_text='JSON с метаданными: информация о файлах, параметрах конвертации и т.д.'
    )
    
    # Дополнительные поля для удобства
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Время создания'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Время обновления'
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время начала выполнения'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время завершения'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    class Meta:
        verbose_name = 'Задача конвертации'
        verbose_name_plural = 'Задачи конвертации'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f'Задача #{self.id} - {self.get_status_display()}'
    
    def set_metadata(self, **kwargs):
        """Удобный метод для установки метаданных"""
        if not self.task_metadata:
            self.task_metadata = {}
        self.task_metadata.update(kwargs)
    
    def get_metadata(self, key, default=None):
        """Удобный метод для получения метаданных"""
        if not self.task_metadata:
            return default
        return self.task_metadata.get(key, default)
    
    def start(self):
        """Пометить задачу как начатую"""
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def complete(self):
        """Пометить задачу как завершенную"""
        self.status = self.STATUS_DONE
        self.progress = 100
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'progress', 'completed_at', 'updated_at'])
    
    def fail(self, error_message=''):
        """Пометить задачу как неудачную"""
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
    
    def update_progress(self, progress):
        """Обновить прогресс выполнения"""
        if 0 <= progress <= 100:
            self.progress = progress
            self.save(update_fields=['progress', 'updated_at'])
    
    @property
    def is_finished(self):
        """Проверить, завершена ли задача"""
        return self.status in [self.STATUS_DONE, self.STATUS_FAILED]
    
    @property
    def is_active(self):
        """Проверить, активна ли задача"""
        return self.status in [self.STATUS_QUEUED, self.STATUS_RUNNING]
    
    @property
    def duration(self):
        """Получить длительность выполнения задачи"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or timezone.now()
        return end_time - self.started_at


class ConversionHistory(models.Model):
    """Модель для хранения истории всех конвертаций"""
    
    # Типы файлов
    FILE_TYPE_VIDEO = 'video'
    FILE_TYPE_IMAGE = 'image'
    FILE_TYPE_AUDIO = 'audio'
    FILE_TYPE_DOCUMENT = 'document'
    FILE_TYPE_ARCHIVE = 'archive'
    FILE_TYPE_OTHER = 'other'
    
    FILE_TYPE_CHOICES = [
        (FILE_TYPE_VIDEO, 'Видео'),
        (FILE_TYPE_IMAGE, 'Изображение'),
        (FILE_TYPE_AUDIO, 'Аудио'),
        (FILE_TYPE_DOCUMENT, 'Документ'),
        (FILE_TYPE_ARCHIVE, 'Архив'),
        (FILE_TYPE_OTHER, 'Другой'),
    ]
    
    # Статусы конвертации
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_COMPLETED, 'Завершено'),
        (STATUS_FAILED, 'Ошибка'),
    ]
    
    # Основные поля
    id = models.AutoField(primary_key=True)
    
    # Информация о файлах
    original_filename = models.CharField(
        max_length=255,
        verbose_name='Оригинальное имя файла'
    )
    
    original_path = models.CharField(
        max_length=512,
        blank=True,
        verbose_name='Путь к оригинальному файлу'
    )
    
    output_filename = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Имя выходного файла'
    )
    
    output_path = models.CharField(
        max_length=512,
        blank=True,
        verbose_name='Путь к результату конвертации'
    )
    
    output_url = models.URLField(
        blank=True,
        verbose_name='URL результата конвертации'
    )
    
    # Метаданные файлов
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        default=FILE_TYPE_OTHER,
        verbose_name='Тип файла'
    )
    
    input_format = models.CharField(
        max_length=10,
        verbose_name='Входной формат'
    )
    
    output_format = models.CharField(
        max_length=10,
        verbose_name='Выходной формат'
    )
    
    file_size = models.BigIntegerField(
        default=0,
        verbose_name='Размер исходного файла (байты)'
    )
    
    output_size = models.BigIntegerField(
        default=0,
        blank=True,
        verbose_name='Размер результата (байты)'
    )
    
    # Информация о конвертации
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_COMPLETED,
        verbose_name='Статус конвертации'
    )
    
    engine_used = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Используемый движок'
    )
    
    processing_time = models.FloatField(
        default=0.0,
        verbose_name='Время обработки (секунды)'
    )
    
    # Параметры конвертации
    conversion_params = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Параметры конвертации',
        help_text='JSON с параметрами конвертации'
    )
    
    # Метаданные результата
    result_metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Метаданные результата',
        help_text='JSON с информацией о результате конвертации'
    )
    
    # Сообщение об ошибке (если есть)
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    # Временные метки
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Время создания'
    )
    
    # IP адрес пользователя (опционально)
    user_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP адрес пользователя'
    )
    
    # User Agent (опционально)
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    
    class Meta:
        verbose_name = 'История конвертации'
        verbose_name_plural = 'История конвертаций'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['file_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['input_format', 'output_format']),
        ]
    
    def __str__(self):
        return f'{self.original_filename} -> {self.output_format} ({self.get_status_display()})'
    
    @property
    def settings_summary(self):
        """Краткое описание настроек конвертации"""
        if not self.conversion_params:
            return 'По умолчанию'
        
        summary_parts = []
        
        # Для видео
        if self.file_type == self.FILE_TYPE_VIDEO:
            if 'width' in self.conversion_params:
                summary_parts.append(f"Ширина: {self.conversion_params['width']}px")
            if 'fps' in self.conversion_params:
                summary_parts.append(f"FPS: {self.conversion_params['fps']}")
            if self.conversion_params.get('grayscale'):
                summary_parts.append('Ч/Б')
        
        # Для изображений
        elif self.file_type == self.FILE_TYPE_IMAGE:
            if 'quality' in self.conversion_params:
                summary_parts.append(f"Качество: {self.conversion_params['quality']}%")
            if 'width' in self.conversion_params:
                summary_parts.append(f"{self.conversion_params['width']}px")
        
        # Для аудио
        elif self.file_type == self.FILE_TYPE_AUDIO:
            if 'bitrate' in self.conversion_params:
                summary_parts.append(f"Битрейт: {self.conversion_params['bitrate']}")
        
        return ', '.join(summary_parts) if summary_parts else 'По умолчанию'
    
    @property
    def compression_ratio(self):
        """Коэффициент сжатия"""
        if not self.file_size or not self.output_size:
            return None
        return round((1 - self.output_size / self.file_size) * 100, 2)
    
    @classmethod
    def create_from_task(cls, task, result_info, **kwargs):
        """Создать запись истории из задачи конвертации"""
        history = cls(
            original_filename=task.get_metadata('original_filename', ''),
            output_filename=result_info.get('output_filename', ''),
            output_path=result_info.get('output_path', ''),
            output_url=result_info.get('output_url', ''),
            file_type=task.get_metadata('file_type', cls.FILE_TYPE_OTHER),
            input_format=task.get_metadata('input_format', ''),
            output_format=result_info.get('output_format', ''),
            file_size=task.get_metadata('file_size', 0),
            output_size=result_info.get('output_size', 0),
            status=cls.STATUS_COMPLETED if task.status == task.STATUS_DONE else cls.STATUS_FAILED,
            engine_used=result_info.get('engine_used', ''),
            processing_time=task.duration.total_seconds() if task.duration else 0,
            conversion_params=task.get_metadata('conversion_params', {}),
            result_metadata=result_info.get('metadata', {}),
            error_message=task.error_message,
            **kwargs
        )
        history.save()
        return history
