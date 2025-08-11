"""
Django команда управления для очистки старых файлов конвертации.

Использование:
    python manage.py cleanup_old_files --days 7
    python manage.py cleanup_old_files --days 7 --dry-run
    python manage.py cleanup_old_files --all-failed
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from converter.models import ConversionTask


class Command(BaseCommand):
    help = 'Очистка старых файлов конвертации и устаревших задач'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Количество дней для хранения файлов (по умолчанию: 7)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет удалено без фактического удаления'
        )
        
        parser.add_argument(
            '--all-failed',
            action='store_true',
            help='Удалить все неудачные задачи независимо от даты'
        )
        
        parser.add_argument(
            '--media-only',
            action='store_true',
            help='Очистить только медиа файлы без удаления задач из БД'
        )
        
        parser.add_argument(
            '--temp-only',
            action='store_true',
            help='Очистить только временные файлы'
        )

    def handle(self, *args, **options):
        self.style.SUCCESS = self.style.SUCCESS
        self.verbosity = options['verbosity']
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('РЕЖИМ ТЕСТИРОВАНИЯ - файлы не будут удалены')
            )
        
        if options['temp_only']:
            self._cleanup_temp_files()
            return
        
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        if self.verbosity >= 1:
            self.stdout.write(
                f'Очистка файлов старше {days} дней '
                f'(до {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")})'
            )
        
        # Статистика
        stats = {
            'old_tasks_deleted': 0,
            'failed_tasks_deleted': 0,
            'media_files_deleted': 0,
            'temp_files_deleted': 0,
            'total_size_freed': 0
        }
        
        # Очистка неудачных задач
        if options['all_failed']:
            stats['failed_tasks_deleted'] = self._cleanup_failed_tasks()
        
        # Очистка старых задач и файлов
        if not options['media_only']:
            stats['old_tasks_deleted'] = self._cleanup_old_tasks(cutoff_date)
        
        stats['media_files_deleted'], freed_media = self._cleanup_media_files(cutoff_date)
        stats['temp_files_deleted'], freed_temp = self._cleanup_temp_files()
        
        stats['total_size_freed'] = freed_media + freed_temp
        
        # Вывод статистики
        self._print_stats(stats)

    def _cleanup_old_tasks(self, cutoff_date):
        """Удаление старых завершенных задач из БД"""
        old_tasks = ConversionTask.objects.filter(
            created_at__lt=cutoff_date,
            status__in=[ConversionTask.STATUS_DONE, ConversionTask.STATUS_FAILED]
        )
        
        count = old_tasks.count()
        
        if self.verbosity >= 2:
            self.stdout.write(f'Найдено {count} старых задач для удаления')
        
        if not self.dry_run and count > 0:
            old_tasks.delete()
            
        return count

    def _cleanup_failed_tasks(self):
        """Удаление всех неудачных задач"""
        failed_tasks = ConversionTask.objects.filter(
            status=ConversionTask.STATUS_FAILED
        )
        
        count = failed_tasks.count()
        
        if self.verbosity >= 2:
            self.stdout.write(f'Найдено {count} неудачных задач для удаления')
        
        if not self.dry_run and count > 0:
            failed_tasks.delete()
            
        return count

    def _cleanup_media_files(self, cutoff_date):
        """Очистка старых медиа файлов"""
        media_root = Path(settings.MEDIA_ROOT)
        gifs_dir = media_root / 'gifs'
        uploads_dir = media_root / 'uploads'
        
        deleted_count = 0
        total_size = 0
        
        # Очистка GIF файлов
        if gifs_dir.exists():
            count, size = self._cleanup_directory(gifs_dir, cutoff_date)
            deleted_count += count
            total_size += size
        
        # Очистка загруженных файлов
        if uploads_dir.exists():
            count, size = self._cleanup_directory(uploads_dir, cutoff_date)
            deleted_count += count
            total_size += size
        
        return deleted_count, total_size

    def _cleanup_temp_files(self):
        """Очистка временных файлов"""
        temp_dir = Path(settings.BASE_DIR) / 'temp'
        
        deleted_count = 0
        total_size = 0
        
        if temp_dir.exists():
            # Удаляем все временные файлы старше 1 дня
            cutoff = timezone.now() - timedelta(days=1)
            count, size = self._cleanup_directory(temp_dir, cutoff)
            deleted_count += count
            total_size += size
        
        return deleted_count, total_size

    def _cleanup_directory(self, directory, cutoff_date):
        """Очистка файлов в директории старше указанной даты"""
        deleted_count = 0
        total_size = 0
        
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    # Проверяем время модификации файла
                    file_time = datetime.fromtimestamp(
                        file_path.stat().st_mtime,
                        tz=timezone.get_current_timezone()
                    )
                    
                    if file_time < cutoff_date:
                        file_size = file_path.stat().st_size
                        
                        if self.verbosity >= 2:
                            self.stdout.write(
                                f'Удаляем: {file_path} '
                                f'({self._format_size(file_size)}, '
                                f'изменен {file_time.strftime("%Y-%m-%d %H:%M:%S")})'
                            )
                        
                        if not self.dry_run:
                            try:
                                file_path.unlink()
                                deleted_count += 1
                                total_size += file_size
                            except OSError as e:
                                self.stderr.write(
                                    f'Ошибка удаления файла {file_path}: {e}'
                                )
                        else:
                            deleted_count += 1
                            total_size += file_size
            
            # Удаляем пустые директории
            if not self.dry_run:
                self._remove_empty_dirs(directory)
                
        except OSError as e:
            self.stderr.write(f'Ошибка доступа к директории {directory}: {e}')
        
        return deleted_count, total_size

    def _remove_empty_dirs(self, directory):
        """Удаление пустых директорий"""
        try:
            for dir_path in sorted(directory.rglob('*'), reverse=True):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    if self.verbosity >= 2:
                        self.stdout.write(f'Удаляем пустую директорию: {dir_path}')
                    dir_path.rmdir()
        except OSError:
            pass  # Игнорируем ошибки при удалении директорий

    def _format_size(self, size_bytes):
        """Форматирование размера файла"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _print_stats(self, stats):
        """Вывод статистики очистки"""
        self.stdout.write(
            self.style.SUCCESS('\n=== СТАТИСТИКА ОЧИСТКИ ===')
        )
        
        if stats['old_tasks_deleted'] > 0:
            self.stdout.write(
                f"Удалено старых задач: {stats['old_tasks_deleted']}"
            )
        
        if stats['failed_tasks_deleted'] > 0:
            self.stdout.write(
                f"Удалено неудачных задач: {stats['failed_tasks_deleted']}"
            )
        
        if stats['media_files_deleted'] > 0:
            self.stdout.write(
                f"Удалено медиа файлов: {stats['media_files_deleted']}"
            )
        
        if stats['temp_files_deleted'] > 0:
            self.stdout.write(
                f"Удалено временных файлов: {stats['temp_files_deleted']}"
            )
        
        if stats['total_size_freed'] > 0:
            self.stdout.write(
                f"Освобождено дискового пространства: "
                f"{self._format_size(stats['total_size_freed'])}"
            )
        
        if all(v == 0 for v in stats.values()):
            self.stdout.write(
                self.style.WARNING('Нет файлов для удаления')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Очистка завершена успешно!')
            )
