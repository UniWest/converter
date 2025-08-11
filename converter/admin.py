from django.contrib import admin
from django.utils.html import format_html
from .models import ConversionTask


@admin.register(ConversionTask)
class ConversionTaskAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'status_colored', 'progress_bar', 'created_at_display', 
        'duration_display', 'get_filename', 'get_format_conversion'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'task_metadata']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at', 'duration_display']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('status', 'progress', 'error_message')
        }),
        ('Метаданные задачи', {
            'fields': ('task_metadata',),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at', 'duration_display'),
            'classes': ('collapse',)
        })
    )
    
    def status_colored(self, obj):
        """Отображение статуса с цветовой индикацией"""
        colors = {
            ConversionTask.STATUS_QUEUED: '#ffc107',    # желтый
            ConversionTask.STATUS_RUNNING: '#007bff',   # синий  
            ConversionTask.STATUS_DONE: '#28a745',      # зеленый
            ConversionTask.STATUS_FAILED: '#dc3545',    # красный
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Статус'
    status_colored.admin_order_field = 'status'
    
    def progress_bar(self, obj):
        """Отображение прогресса в виде прогресс-бара"""
        if obj.progress == 0:
            color = '#6c757d'  # серый
        elif obj.progress < 50:
            color = '#ffc107'  # желтый
        elif obj.progress < 100:
            color = '#007bff'  # синий
        else:
            color = '#28a745'  # зеленый
            
        return format_html(
            '<div style="width: 100px; height: 20px; background-color: #e9ecef; border-radius: 4px; overflow: hidden;">' +
            '<div style="width: {}%; height: 100%; background-color: {}; transition: width 0.3s;"></div>' +
            '</div><span style="margin-left: 5px;">{}%</span>',
            obj.progress, color, obj.progress
        )
    progress_bar.short_description = 'Прогресс'
    progress_bar.admin_order_field = 'progress'
    
    def created_at_display(self, obj):
        """Красивое отображение времени создания"""
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    created_at_display.short_description = 'Создано'
    created_at_display.admin_order_field = 'created_at'
    
    def duration_display(self, obj):
        """Отображение длительности выполнения"""
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f'{hours}ч {minutes}м {seconds}с'
            elif minutes > 0:
                return f'{minutes}м {seconds}с'
            else:
                return f'{seconds}с'
        return '-'
    duration_display.short_description = 'Длительность'
    
    def get_filename(self, obj):
        """Получить имя исходного файла из метаданных"""
        return obj.get_metadata('original_filename', 'Не указано')
    get_filename.short_description = 'Файл'
    
    def get_format_conversion(self, obj):
        """Получить информацию о конвертации форматов"""
        input_format = obj.get_metadata('input_format', '?')
        output_format = obj.get_metadata('output_format', '?')
        return f'{input_format.upper()} → {output_format.upper()}'
    get_format_conversion.short_description = 'Конвертация'
    
    def has_add_permission(self, request):
        """Запретить создание задач через админку"""
        return False
    
    actions = ['restart_failed_tasks']
    
    def restart_failed_tasks(self, request, queryset):
        """Действие для перезапуска неудачных задач"""
        failed_tasks = queryset.filter(status=ConversionTask.STATUS_FAILED)
        count = 0
        for task in failed_tasks:
            task.status = ConversionTask.STATUS_QUEUED
            task.progress = 0
            task.error_message = ''
            task.started_at = None
            task.completed_at = None
            task.save()
            count += 1
        
        self.message_user(
            request,
            f'Перезапущено {count} задач(и).'
        )
    restart_failed_tasks.short_description = 'Перезапустить неудачные задачи'
