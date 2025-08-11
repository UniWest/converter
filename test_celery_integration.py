#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестирование интеграции Celery с Django
Проверка всех компонентов системы асинхронной обработки
"""

import time
import logging
from pathlib import Path

# Настройка Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
django.setup()

    convert_video, convert_audio, convert_image, 
    convert_document, convert_archive, cleanup_old_files
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class CeleryIntegrationTester:
    """Класс для тестирования интеграции Celery"""

    def __init__(self):
        self.test_files = {}
        self.temp_dir = Path(tempfile.mkdtemp())
        logger.info(f'Временная директория для тестов: {self.temp_dir}')

    def setup_test_files(self):
        """Создание тестовых файлов"""
        logger.info('Создание тестовых файлов...')

        # Простой текстовый файл
        text_file = self.temp_dir / 'test.txt'
        text_file.write_text('Тестовый файл для конвертации документов\nСтрока 2\nСтрока 3')
        self.test_files['document'] = str(text_file)

        # Создание простого изображения (если есть Pillow)
        try:
from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')
            img_file = self.temp_dir / 'test.png'
            img.save(str(img_file))
            self.test_files['image'] = str(img_file)
            logger.info('Тестовое изображение создано')
        except ImportError:
            logger.warning('Pillow не установлен, пропускаем создание тестового изображения')

        logger.info(f'Созданы тестовые файлы: {list(self.test_files.keys())}')

    def test_redis_connection(self):
        """Проверка соединения с Redis"""
        logger.info('Тестирование соединения с Redis...')

        try:
import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            if r.ping():
                logger.info('✅ Redis доступен')
                return True
            else:
                logger.error('❌ Redis недоступен')
                return False
        except Exception as e:
            logger.error(f'❌ Ошибка соединения с Redis: {e}')
            return False

    def test_celery_worker_status(self):
        """Проверка статуса Celery воркеров"""
        logger.info('Проверка статуса Celery воркеров...')

        try:
from converter_site.celery import app

            inspect = app.control.inspect()

            # Проверка активных воркеров
            stats = inspect.stats()
            if stats:
                logger.info(f'✅ Активные воркеры: {list(stats.keys())}')

                # Подробная информация о воркерах
                for worker_name, worker_stats in stats.items():
                logger.info(f'  {worker_name}: {worker_stats.get("pool", {}).get("max-concurrency", "N/A")} потоков')

                return True
            else:
                logger.warning('⚠️  Нет активных воркеров')
                return False

        except Exception as e:
            logger.error(f'❌ Ошибка проверки воркеров: {e}')
            return False

    def test_task_creation(self):
        """Тестирование создания задач в базе данных"""
        logger.info('Тестирование создания задач в БД...')

        try:
            # Создание тестовой задачи
            task = ConversionTask.objects.create()
            task.set_metadata(
                test_task=True,
                input_file='test.txt',
                output_format='pdf'
            )
            task.save()

            logger.info(f'✅ Задача создана: ID={task.id}, статус={task.status}')

            # Проверка методов модели
            task.start()
            logger.info(f'  Задача запущена: статус={task.status}')

            task.update_progress(50)
            logger.info(f'  Прогресс обновлён: {task.progress}%')

            task.complete()
            logger.info(f'  Задача завершена: статус={task.status}')

            # Очистка
            task.delete()
            logger.info('  Тестовая задача удалена')

            return True

        except Exception as e:
            logger.error(f'❌ Ошибка тестирования модели задач: {e}')
            return False

    def test_debug_task(self):
        """Тестирование простой отладочной задачи"""
        logger.info('Тестирование отладочной задачи...')

        try:
from converter_site.celery import debug_task

            # Запуск отладочной задачи
            result = debug_task.delay()
            logger.info(f'✅ Отладочная задача отправлена: {result.task_id}')

            # Ожидание результата (максимум 10 секунд)
            timeout = 10
            start_time = time.time()

            while not result.ready() and (time.time() - start_time) < timeout:
                time.sleep(0.5)
                logger.info('  Ожидание выполнения...')

            if result.ready():
                if result.successful():
                logger.info(f'✅ Отладочная задача выполнена успешно: {result.result}')
                return True
                else:
                logger.error(f'❌ Отладочная задача завершилась с ошибкой: {result.result}')
                return False
            else:
                logger.warning('⚠️  Отладочная задача не завершилась за отведённое время')
                return False

        except Exception as e:
            logger.error(f'❌ Ошибка тестирования отладочной задачи: {e}')
            return False

    def test_document_conversion_task(self):
        """Тестирование задачи конвертации документов"""
        if 'document' not in self.test_files:
            logger.warning('⚠️  Тестовый документ не создан, пропускаем тест')
            return True

        logger.info('Тестирование задачи конвертации документов...')

        try:
            # Создание задачи в БД
            task = ConversionTask.objects.create()
            task.set_metadata(
                input_file=self.test_files['document'],
                output_format='html',
                test_task=True
            )
            task.save()

            # Отправка задачи в Celery
            result = convert_document.delay(
                task_id=str(task.id),
                input_path=self.test_files['document'],
                output_format='html'
            )

            logger.info(f'✅ Задача конвертации документа отправлена: {result.task_id}')

            # Мониторинг выполнения
            timeout = 30
            start_time = time.time()

            while not result.ready() and (time.time() - start_time) < timeout:
                # Обновляем информацию о задаче из БД
                task.refresh_from_db()
                logger.info(f'  Статус: {task.status}, прогресс: {task.progress}%')
                time.sleep(2)

            if result.ready():
                task.refresh_from_db()
                if result.successful() and task.status == ConversionTask.STATUS_DONE:
                logger.info('✅ Задача конвертации документа выполнена успешно')
                return True
                else:
                logger.error(f'❌ Задача конвертации документа завершилась с ошибкой: {task.error_message}')
                return False
            else:
                logger.warning('⚠️  Задача конвертации документа не завершилась за отведённое время')
                return False

        except Exception as e:
            logger.error(f'❌ Ошибка тестирования конвертации документа: {e}')
            return False
        finally:
            # Очистка
            try:
                if 'task' in locals():
                task.delete()
            except:
                pass

    def test_cleanup_task(self):
        """Тестирование задачи очистки"""
        logger.info('Тестирование задачи очистки...')

        try:
            # Создание тестовой директории с файлами
            cleanup_test_dir = self.temp_dir / 'cleanup_test'
            cleanup_test_dir.mkdir(exist_ok=True)

            # Создание нескольких тестовых файлов
            for i in range(3):
                test_file = cleanup_test_dir / f'test_{i}.txt'
                test_file.write_text(f'Тестовый файл {i}')

            logger.info(f'Создано 3 тестовых файла в {cleanup_test_dir}')

            # Запуск задачи очистки (файлы возрастом 0 часов, т.е. все)
            result = cleanup_old_files.delay(max_age_hours=0)

            logger.info(f'✅ Задача очистки отправлена: {result.task_id}')

            # Ожидание выполнения
            timeout = 20
            start_time = time.time()

            while not result.ready() and (time.time() - start_time) < timeout:
                time.sleep(1)
                logger.info('  Выполнение задачи очистки...')

            if result.ready() and result.successful():
                cleanup_result = result.result
                logger.info(f'✅ Задача очистки выполнена: {cleanup_result}')
                return True
            else:
                logger.error(f'❌ Задача очистки завершилась с ошибкой')
                return False

        except Exception as e:
            logger.error(f'❌ Ошибка тестирования задачи очистки: {e}')
            return False

    def test_task_monitoring(self):
        """Тестирование мониторинга задач"""
        logger.info('Тестирование мониторинга задач...')

        try:
from converter_site.celery import app

            inspect = app.control.inspect()

            # Активные задачи
            active = inspect.active()
            if active:
                logger.info(f'✅ Активные задачи: {sum(len(tasks) for tasks in active.values())}')
            else:
                logger.info('✅ Нет активных задач')

            # Зарегистрированные задачи
            registered = inspect.registered()
            if registered:
                total_tasks = sum(len(tasks) for tasks in registered.values())
                logger.info(f'✅ Зарегистрировано задач: {total_tasks}')

                # Выводим первые несколько задач
                all_tasks = []
                for worker_tasks in registered.values():
                all_tasks.extend(worker_tasks)

                logger.info('  Доступные задачи:')
                for task in all_tasks[:5]:  # Первые 5 задач
                logger.info(f'    - {task}')

                if len(all_tasks) > 5:
                logger.info(f'    ... и ещё {len(all_tasks) - 5} задач')

            return True

        except Exception as e:
            logger.error(f'❌ Ошибка тестирования мониторинга: {e}')
            return False

    def run_all_tests(self):
        """Запуск всех тестов"""
        logger.info('=' * 60)
        logger.info('НАЧАЛО ТЕСТИРОВАНИЯ ИНТЕГРАЦИИ CELERY')
        logger.info('=' * 60)

        tests = [
            ('Соединение с Redis', self.test_redis_connection),
            ('Создание тестовых файлов', self.setup_test_files),
            ('Статус Celery воркеров', self.test_celery_worker_status),
            ('Создание задач в БД', self.test_task_creation),
            ('Отладочная задача', self.test_debug_task),
            ('Конвертация документов', self.test_document_conversion_task),
            ('Задача очистки', self.test_cleanup_task),
            ('Мониторинг задач', self.test_task_monitoring),
        ]

        results = {}

        for test_name, test_func in tests:
            logger.info('-' * 40)
            logger.info(f'ТЕСТ: {test_name}')
            logger.info('-' * 40)

            try:
                if callable(test_func):
                results[test_name] = test_func()
                else:
                results[test_name] = test_func
            except Exception as e:
                logger.error(f'❌ Критическая ошибка в тесте "{test_name}": {e}')
                results[test_name] = False

        # Итоговый отчёт
        logger.info('=' * 60)
        logger.info('ИТОГОВЫЙ ОТЧЁТ')
        logger.info('=' * 60)

        passed = 0
        total = len(results)

        for test_name, result in results.items():
            status = '✅ ПРОЙДЕН' if result else '❌ ПРОВАЛЕН'
            logger.info(f'{test_name:.<40} {status}')
            if result:
                passed += 1

        logger.info('-' * 60)
        logger.info(f'ВСЕГО ТЕСТОВ: {total}')
        logger.info(f'ПРОЙДЕНО: {passed}')
        logger.info(f'ПРОВАЛЕНО: {total - passed}')
        logger.info(f'УСПЕШНОСТЬ: {passed/total*100:.1f}%')

        if passed == total:
            logger.info('🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!')
            logger.info('Система Celery готова к работе.')
        elif passed >= total * 0.8:
            logger.info('⚠️  БОЛЬШИНСТВО ТЕСТОВ ПРОЙДЕНО')
            logger.info('Система частично готова, но есть проблемы.')
        else:
            logger.info('❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ')
            logger.info('Система НЕ готова к работе.')

        logger.info('=' * 60)

        return passed == total

    def cleanup(self):
        """Очистка тестовых файлов"""
        logger.info('Очистка тестовых файлов...')
        try:
import shutil
            shutil.rmtree(str(self.temp_dir))
            logger.info('✅ Тестовые файлы удалены')
        except Exception as e:
            logger.warning(f'⚠️  Не удалось очистить тестовые файлы: {e}')


def main():
    """Главная функция"""
    try:
        tester = CeleryIntegrationTester()
        success = tester.run_all_tests()
        tester.cleanup()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info('\n⚠️  Тестирование прервано пользователем')
        sys.exit(130)
    except Exception as e:
        logger.error(f'❌ Критическая ошибка: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
