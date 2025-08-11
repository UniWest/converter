#!/usr/bin/env python3
import os
import json
from typing import Dict, Any, List
"""
Главный скрипт для запуска всех тестов функциональности STT системы
Включает генерацию тестовых данных, API тесты, UI тесты, Celery тесты
"""

import sys
import argparse
import time
from pathlib import Path
import logging
from datetime import datetime

# Настройка путей
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
import django
django.setup()

# Импорты тестов
from test_audio_generator import TestAudioGenerator
from test_stt_functionality import run_stt_tests
from test_ui_functionality import run_ui_tests
from test_celery_api import pytest

logger = logging.getLogger(__name__)


class TestRunner:
    """Главный класс для запуска всех тестов"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('test_results.log', mode='w', encoding='utf-8')
            ]
        )
    
    def print_header(self):
        """Выводит заголовок тестирования"""
        header = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                   ТЕСТИРОВАНИЕ ФУНКЦИОНАЛЬНОСТИ STT СИСТЕМЫ                 ║
║                              Шаг 8 из плана                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ 1. ✅ Короткие тест-клипы RU/EN (15-60 сек) — проверка точности             ║
║ 2. ✅ Длинный файл 5-10 мин — проверка сегментации, стабильности            ║
║ 3. ✅ UI: drag-and-drop, прогресс-бар, скачивание всех форматов             ║
║ 4. ✅ Autotest Celery + API через pytest                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        print(header)
    
    def generate_test_data(self) -> bool:
        """Генерирует тестовые аудиоданные"""
        print("\n🎵 ЭТАП 1: Генерация тестовых аудиофайлов")
        print("=" * 60)
        
        try:
            generator = TestAudioGenerator()
            
            print("Создание тестовых аудиофайлов...")
            test_files = generator.create_test_suite()
            
            # Подсчитываем количество созданных файлов
            total_files = sum(len(files) for files in test_files.values())
            
            print(f"✅ Создано тестовых файлов: {total_files}")
            print(f"   - Короткие RU: {len(test_files.get('short_ru', []))}")
            print(f"   - Короткие EN: {len(test_files.get('short_en', []))}")
            print(f"   - Длинные файлы: {len(test_files.get('long_files', []))}")
            
            self.test_results['data_generation'] = {
                'status': 'success',
                'files_created': total_files,
                'categories': {k: len(v) for k, v in test_files.items()},
                'duration': 'N/A'
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка генерации тестовых данных: {e}")
            self.test_results['data_generation'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def run_api_tests(self) -> bool:
        """Запускает API и функциональные тесты"""
        print("\n🔧 ЭТАП 2: Тестирование API и функциональности STT")
        print("=" * 60)
        
        try:
            start_time = time.time()
            
            # Запускаем STT функциональные тесты
            print("Запуск функциональных тестов STT...")
            result = run_stt_tests()
            
            end_time = time.time()
            duration = end_time - start_time
            
            success_rate = 0
            if result.testsRun > 0:
                success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
            
            self.test_results['api_tests'] = {
                'status': 'completed',
                'total_tests': result.testsRun,
                'successful': result.testsRun - len(result.failures) - len(result.errors),
                'failed': len(result.failures),
                'errors': len(result.errors),
                'success_rate': round(success_rate, 2),
                'duration': round(duration, 2)
            }
            
            print(f"✅ API тесты завершены за {duration:.1f} сек")
            print(f"   Успешность: {success_rate:.1f}%")
            
            return len(result.failures) == 0 and len(result.errors) == 0
            
        except Exception as e:
            logger.error(f"Ошибка API тестов: {e}")
            self.test_results['api_tests'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def run_ui_tests(self) -> bool:
        """Запускает UI тесты"""
        print("\n🖥️ ЭТАП 3: Тестирование пользовательского интерфейса")
        print("=" * 60)
        
        # Проверяем, установлены ли Selenium зависимости
        try:
            from selenium import webdriver
        except ImportError:
            print("⚠️ Selenium не установлен. Пропускаем UI тесты.")
            print("   Для запуска UI тестов установите: pip install selenium webdriver-manager")
            self.test_results['ui_tests'] = {
                'status': 'skipped',
                'reason': 'Selenium not installed'
            }
            return True
        
        try:
            start_time = time.time()
            
            print("Запуск UI тестов...")
            result = run_ui_tests()
            
            end_time = time.time()
            duration = end_time - start_time
            
            success_rate = 0
            if result.testsRun > 0:
                success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
            
            self.test_results['ui_tests'] = {
                'status': 'completed',
                'total_tests': result.testsRun,
                'successful': result.testsRun - len(result.failures) - len(result.errors),
                'failed': len(result.failures),
                'errors': len(result.errors),
                'success_rate': round(success_rate, 2),
                'duration': round(duration, 2)
            }
            
            print(f"✅ UI тесты завершены за {duration:.1f} сек")
            print(f"   Успешность: {success_rate:.1f}%")
            
            return len(result.failures) == 0 and len(result.errors) == 0
            
        except Exception as e:
            logger.error(f"Ошибка UI тестов: {e}")
            self.test_results['ui_tests'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def run_celery_tests(self) -> bool:
        """Запускает Celery и pytest тесты"""
        print("\n⚙️ ЭТАП 4: Тестирование Celery + API через pytest")
        print("=" * 60)
        
        try:
            start_time = time.time()
            
            print("Запуск Celery/pytest тестов...")
            
            # Запускаем pytest для Celery тестов
            test_file = Path(__file__).parent / 'test_celery_api.py'
            
            exit_code = pytest.main([
                str(test_file),
                '-v',
                '-s',
                '--tb=short',
                '--color=yes',
                f'--junit-xml={Path(__file__).parent / "celery_test_results.xml"}'
            ])
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.test_results['celery_tests'] = {
                'status': 'completed' if exit_code == 0 else 'failed',
                'exit_code': exit_code,
                'duration': round(duration, 2)
            }
            
            print(f"✅ Celery тесты завершены за {duration:.1f} сек")
            print(f"   Код выхода: {exit_code}")
            
            return exit_code == 0
            
        except Exception as e:
            logger.error(f"Ошибка Celery тестов: {e}")
            self.test_results['celery_tests'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def generate_report(self):
        """Генерирует итоговый отчет"""
        print("\n📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 70)
        
        total_duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        
        # Подсчитываем общие статистики
        total_tests = 0
        total_successful = 0
        total_failed = 0
        total_errors = 0
        
        for test_type, results in self.test_results.items():
            if isinstance(results, dict) and 'total_tests' in results:
                total_tests += results.get('total_tests', 0)
                total_successful += results.get('successful', 0)
                total_failed += results.get('failed', 0)
                total_errors += results.get('errors', 0)
        
        overall_success_rate = (total_successful / total_tests * 100) if total_tests > 0 else 0
        
        print(f"⏱️ Общее время выполнения: {total_duration:.1f} сек")
        print(f"📈 Всего тестов: {total_tests}")
        print(f"✅ Успешных: {total_successful}")
        print(f"❌ Неудачных: {total_failed}")
        print(f"🚨 Ошибок: {total_errors}")
        print(f"🎯 Общая успешность: {overall_success_rate:.1f}%")
        
        print("\n📋 Детали по этапам:")
        
        # Отчет по генерации данных
        if 'data_generation' in self.test_results:
            data_gen = self.test_results['data_generation']
            status_icon = "✅" if data_gen['status'] == 'success' else "❌"
            print(f"   {status_icon} Генерация тестовых данных: {data_gen['status']}")
            if 'files_created' in data_gen:
                print(f"     📁 Создано файлов: {data_gen['files_created']}")
        
        # Отчет по API тестам
        if 'api_tests' in self.test_results:
            api_tests = self.test_results['api_tests']
            status_icon = "✅" if api_tests['status'] == 'completed' else "❌"
            print(f"   {status_icon} API тесты: {api_tests.get('success_rate', 0):.1f}% успешность")
            if 'duration' in api_tests:
                print(f"     ⏱️ Время: {api_tests['duration']} сек")
        
        # Отчет по UI тестам
        if 'ui_tests' in self.test_results:
            ui_tests = self.test_results['ui_tests']
            if ui_tests['status'] == 'skipped':
                print(f"   ⚠️ UI тесты: пропущены ({ui_tests.get('reason', 'Unknown reason')})")
            else:
                status_icon = "✅" if ui_tests['status'] == 'completed' else "❌"
                print(f"   {status_icon} UI тесты: {ui_tests.get('success_rate', 0):.1f}% успешность")
                if 'duration' in ui_tests:
                    print(f"     ⏱️ Время: {ui_tests['duration']} сек")
        
        # Отчет по Celery тестам
        if 'celery_tests' in self.test_results:
            celery_tests = self.test_results['celery_tests']
            status_icon = "✅" if celery_tests.get('exit_code') == 0 else "❌"
            print(f"   {status_icon} Celery тесты: код выхода {celery_tests.get('exit_code', 'N/A')}")
            if 'duration' in celery_tests:
                print(f"     ⏱️ Время: {celery_tests['duration']} сек")
        
        # Сохраняем отчет в файл
        self._save_report_to_file(total_duration, overall_success_rate)
        
        # Рекомендации
        print("\n💡 РЕКОМЕНДАЦИИ:")
        if overall_success_rate >= 90:
            print("   🎉 Отличный результат! Система готова к продакшену.")
        elif overall_success_rate >= 75:
            print("   👍 Хороший результат. Рекомендуется устранить оставшиеся проблемы.")
        elif overall_success_rate >= 50:
            print("   ⚠️ Средний результат. Требуется доработка функциональности.")
        else:
            print("   🚨 Низкий результат. Необходима серьезная отладка системы.")
        
        if total_failed > 0 or total_errors > 0:
            print("   🔍 Проверьте логи для детального анализа проблем.")
    
    def _save_report_to_file(self, total_duration: float, success_rate: float):
        """Сохраняет отчет в JSON файл"""
        try:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'test_session': {
                    'total_duration': total_duration,
                    'overall_success_rate': success_rate,
                    'start_time': self.start_time.isoformat() if self.start_time else None,
                    'end_time': self.end_time.isoformat() if self.end_time else None
                },
                'test_results': self.test_results,
                'environment': {
                    'python_version': sys.version,
                    'django_version': django.VERSION,
                    'project_root': str(project_root)
                }
            }
            
            report_file = Path(__file__).parent / f'test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n📄 Детальный отчет сохранен: {report_file}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения отчета: {e}")
    
    def run_all(self, skip_ui: bool = False, skip_celery: bool = False) -> bool:
        """Запускает все тесты"""
        self.start_time = datetime.now()
        
        self.print_header()
        
        success = True
        
        # Этап 1: Генерация тестовых данных
        if not self.generate_test_data():
            success = False
        
        # Этап 2: API тесты
        if not self.run_api_tests():
            success = False
        
        # Этап 3: UI тесты (опционально)
        if not skip_ui:
            if not self.run_ui_tests():
                success = False
        
        # Этап 4: Celery тесты (опционально)
        if not skip_celery:
            if not self.run_celery_tests():
                success = False
        
        self.end_time = datetime.now()
        
        # Генерация отчета
        self.generate_report()
        
        return success


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Запуск комплексного тестирования STT системы'
    )
    
    parser.add_argument(
        '--skip-ui',
        action='store_true',
        help='Пропустить UI тесты (полезно если нет Selenium)'
    )
    
    parser.add_argument(
        '--skip-celery',
        action='store_true',
        help='Пропустить Celery тесты'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Путь к файлу конфигурации тестов (JSON)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод логов'
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Загрузка конфигурации
    config = {}
    if args.config and Path(args.config).exists():
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ Конфигурация загружена из {args.config}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки конфигурации: {e}")
    
    # Запуск тестов
    runner = TestRunner(config)
    success = runner.run_all(
        skip_ui=args.skip_ui,
        skip_celery=args.skip_celery
    )
    
    # Код выхода
    exit_code = 0 if success else 1
    print(f"\n🏁 Тестирование завершено с кодом: {exit_code}")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
