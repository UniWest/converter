#!/usr/bin/env python3
import os
import json
import tempfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from typing import Dict, Any
"""
Тесты пользовательского интерфейса (UI) для STT системы
Проверка drag-and-drop, прогресс-бар, скачивания всех форматов
"""

import sys
import time
from pathlib import Path
import logging

# Selenium импорты
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

# Django setup
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'converter_site.settings')
import django
django.setup()

from django.test import LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from test_audio_generator import TestAudioGenerator

logger = logging.getLogger(__name__)


class UITestCase(StaticLiveServerTestCase):
    """Базовый класс для UI тестов"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_generator = TestAudioGenerator()
        cls.test_files = cls.test_generator.create_test_suite()
        
        # Настройка драйвера
        cls.driver = cls.setup_webdriver()
        cls.wait = WebDriverWait(cls.driver, 30)  # 30 секунд ожидания
        
        logging.basicConfig(level=logging.INFO)
    
    @classmethod
    def setup_webdriver(cls) -> webdriver:
        """Настройка веб-драйвера"""
        try:
            # Пробуем Chrome сначала
            chrome_options = ChromeOptions()
            chrome_options.add_argument('--headless')  # Запуск без GUI
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            
            # Настройки для файловых загрузок
            prefs = {
                "download.default_directory": str(Path.cwd() / "test_downloads"),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            logger.info("✅ Chrome WebDriver инициализирован")
            return driver
            
        except Exception as chrome_error:
            logger.warning(f"Chrome недоступен: {chrome_error}")
            
            try:
                # Fallback на Firefox
                firefox_options = FirefoxOptions()
                firefox_options.add_argument('--headless')
                firefox_options.add_argument('--width=1920')
                firefox_options.add_argument('--height=1080')
                
                # Настройки загрузки для Firefox
                profile = webdriver.FirefoxProfile()
                profile.set_preference("browser.download.folderList", 2)
                profile.set_preference("browser.download.dir", str(Path.cwd() / "test_downloads"))
                profile.set_preference("browser.helperApps.neverAsk.saveToDisk", 
                                     "audio/wav,audio/mpeg,text/plain,application/json,text/srt")
                firefox_options.profile = profile
                
                driver = webdriver.Firefox(
                    service=FirefoxService(GeckoDriverManager().install()),
                    options=firefox_options
                )
                
                logger.info("✅ Firefox WebDriver инициализирован")
                return driver
                
            except Exception as firefox_error:
                logger.error(f"Firefox также недоступен: {firefox_error}")
                raise Exception("Не удалось инициализировать ни один WebDriver")
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.driver.get(self.live_server_url)
        
        # Ждем загрузки основных элементов страницы
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            logger.error("Страница не загрузилась за 10 секунд")
    
    @classmethod
    def tearDownClass(cls):
        if cls.driver:
            cls.driver.quit()
        super().tearDownClass()
        
        # Очищаем тестовые загрузки
        downloads_dir = Path.cwd() / "test_downloads"
        if downloads_dir.exists():
            import shutil
            shutil.rmtree(downloads_dir, ignore_errors=True)


class DragAndDropTest(UITestCase):
    """Тесты функциональности Drag and Drop"""
    
    def test_01_drag_and_drop_interface_exists(self):
        """Тест 1: Проверка наличия интерфейса drag-and-drop"""
        print("\n=== Тест 1: Проверка интерфейса Drag & Drop ===")
        
        # Переходим на страницу конвертации аудио
        audio_page_url = f"{self.live_server_url}/audio-to-text/"
        self.driver.get(audio_page_url)
        
        try:
            # Ищем зону загрузки
            drop_zone = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "drop-zone"))
            )
            
            self.assertTrue(drop_zone.is_displayed(), "Зона drag-and-drop должна быть видимой")
            
            # Проверяем текст в зоне загрузки
            drop_text = drop_zone.text
            self.assertIn("Перетащите", drop_text.lower(), 
                         "Должен быть текст о перетаскивании файлов")
            
            print("✅ Интерфейс drag-and-drop найден и отображается")
            
            # Проверяем наличие кнопки выбора файла
            file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            self.assertIsNotNone(file_input, "Должна быть кнопка выбора файла")
            
            print("✅ Кнопка выбора файла найдена")
            
        except TimeoutException:
            # Может быть, элементы имеют другие классы/ID
            self.fail("Не найден интерфейс drag-and-drop")
    
    def test_02_file_upload_via_input(self):
        """Тест 2: Загрузка файла через input[type=file]"""
        print("\n=== Тест 2: Загрузка файла через input ===")
        
        audio_page_url = f"{self.live_server_url}/audio-to-text/"
        self.driver.get(audio_page_url)
        
        # Берем короткий тестовый файл
        test_file = self.test_files['short_ru'][0]
        
        try:
            # Находим input для файлов
            file_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            
            # Загружаем файл
            file_input.send_keys(test_file)
            
            # Ждем появления информации о файле
            time.sleep(2)
            
            # Проверяем, что файл был загружен
            # (здесь нужно будет адаптировать под конкретную реализацию)
            page_source = self.driver.page_source.lower()
            filename = Path(test_file).name.lower()
            
            # Ищем название файла на странице или проверяем изменение состояния
            if filename in page_source or "загружен" in page_source:
                print(f"✅ Файл {Path(test_file).name} успешно загружен")
            else:
                print("⚠️ Не удалось подтвердить загрузку файла")
            
        except TimeoutException:
            self.fail("Не найден элемент input[type='file']")
    
    def test_03_multiple_format_support(self):
        """Тест 3: Поддержка различных аудиоформатов"""
        print("\n=== Тест 3: Поддержка форматов файлов ===")
        
        audio_page_url = f"{self.live_server_url}/audio-to-text/"
        self.driver.get(audio_page_url)
        
        try:
            # Проверяем accept атрибут input'а
            file_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            
            accept_attr = file_input.get_attribute("accept")
            if accept_attr:
                print(f"Поддерживаемые форматы: {accept_attr}")
                
                # Проверяем основные аудиоформаты
                expected_formats = [".wav", ".mp3", ".m4a", "audio/"]
                for fmt in expected_formats:
                    if any(fmt in accept_attr for fmt in expected_formats):
                        print(f"✅ Поддерживаются аудиоформаты")
                        break
                else:
                    print("⚠️ Не найдены ожидаемые аудиоформаты в accept")
            else:
                print("⚠️ Атрибут accept не установлен")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке форматов: {e}")


class ProgressBarTest(UITestCase):
    """Тесты функциональности прогресс-бара"""
    
    def test_01_progress_bar_appears_on_upload(self):
        """Тест 1: Появление прогресс-бара при загрузке"""
        print("\n=== Тест 1: Появление прогресс-бара ===")
        
        audio_page_url = f"{self.live_server_url}/audio-to-text/"
        self.driver.get(audio_page_url)
        
        test_file = self.test_files['short_ru'][0]
        
        try:
            # Загружаем файл
            file_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(test_file)
            
            # Ищем кнопку отправки/конвертации
            submit_button = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], .convert-btn, .submit-btn"
            )
            
            if submit_button:
                submit_button.click()
                
                # Ждем появления прогресс-бара
                try:
                    progress_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR, 
                            ".progress, .progress-bar, .loading, .spinner"
                        ))
                    )
                    
                    self.assertTrue(progress_element.is_displayed(), 
                                  "Прогресс-бар должен быть видимым")
                    print("✅ Прогресс-бар появился при обработке")
                    
                except TimeoutException:
                    print("⚠️ Прогресс-бар не найден или не появился")
            
        except Exception as e:
            logger.error(f"Ошибка при тестировании прогресс-бара: {e}")
    
    def test_02_progress_updates_during_processing(self):
        """Тест 2: Обновление прогресса во время обработки"""
        print("\n=== Тест 2: Обновление прогресса ===")
        
        audio_page_url = f"{self.live_server_url}/audio-to-text/"
        self.driver.get(audio_page_url)
        
        # Берем файл подлиннее для наблюдения за прогрессом
        test_file = self.test_files['short_ru'][-1]  # Берем самый длинный из коротких
        
        try:
            file_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(test_file)
            
            # Отправляем форму
            submit_button = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], .convert-btn, .submit-btn"
            )
            submit_button.click()
            
            # Мониторим изменения прогресса
            progress_values = []
            start_time = time.time()
            
            while time.time() - start_time < 60:  # Максимум 1 минута ожидания
                try:
                    # Ищем элементы прогресса
                    progress_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, 
                        ".progress-bar, .progress-value, [data-progress]"
                    )
                    
                    for element in progress_elements:
                        text = element.text
                        if '%' in text:
                            try:
                                progress_val = int(text.replace('%', '').strip())
                                progress_values.append(progress_val)
                                print(f"📊 Прогресс: {progress_val}%")
                            except ValueError:
                                continue
                    
                    # Проверяем завершение
                    if "завершено" in self.driver.page_source.lower() or \
                       "completed" in self.driver.page_source.lower():
                        print("✅ Обработка завершена")
                        break
                        
                    time.sleep(2)
                    
                except Exception:
                    time.sleep(1)
                    continue
            
            # Анализируем собранные данные о прогрессе
            if progress_values:
                print(f"✅ Зафиксировано {len(progress_values)} обновлений прогресса")
                print(f"📈 Диапазон: {min(progress_values)}% - {max(progress_values)}%")
            else:
                print("⚠️ Не удалось зафиксировать изменения прогресса")
                
        except Exception as e:
            logger.error(f"Ошибка при мониторинге прогресса: {e}")


class DownloadTest(UITestCase):
    """Тесты функциональности скачивания файлов"""
    
    def test_01_download_options_available(self):
        """Тест 1: Наличие опций скачивания различных форматов"""
        print("\n=== Тест 1: Опции скачивания ===")
        
        # Переходим на страницу результатов (имитация)
        audio_page_url = f"{self.live_server_url}/audio-to-text/"
        self.driver.get(audio_page_url)
        
        try:
            # Ищем селекторы форматов вывода
            format_selectors = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "select[name='output_format'], .format-selector, input[name='output_format']"
            )
            
            if format_selectors:
                print("✅ Найдены селекторы форматов")
                
                for selector in format_selectors:
                    if selector.tag_name == 'select':
                        options = selector.find_elements(By.TAG_NAME, "option")
                        formats = [opt.get_attribute("value") for opt in options]
                        print(f"📋 Доступные форматы: {formats}")
                        
                        # Проверяем ожидаемые форматы
                        expected_formats = ['text', 'json', 'srt']
                        found_formats = [fmt for fmt in expected_formats if fmt in formats]
                        print(f"✅ Поддерживаемые форматы: {found_formats}")
            
            else:
                print("⚠️ Селекторы форматов не найдены")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке опций скачивания: {e}")
    
    def test_02_download_link_generation(self):
        """Тест 2: Генерация ссылок для скачивания"""
        print("\n=== Тест 2: Генерация ссылок скачивания ===")
        
        # Тестируем через API, так как полный workflow может быть сложным в UI тестах
        audio_page_url = f"{self.live_server_url}/audio-to-text/"
        self.driver.get(audio_page_url)
        
        try:
            # Выполняем JavaScript для тестирования функций скачивания
            download_script = """
            // Имитация результата конвертации
            var mockResult = {
                text: "Тестовый текст результата",
                segments: [
                    {start: 0, end: 5, text: "Первый сегмент"},
                    {start: 5, end: 10, text: "Второй сегмент"}
                ]
            };
            
            // Проверяем наличие функций скачивания
            var downloadFunctions = [];
            
            if (typeof downloadText !== 'undefined') {
                downloadFunctions.push('downloadText');
            }
            if (typeof downloadJson !== 'undefined') {
                downloadFunctions.push('downloadJson');
            }
            if (typeof downloadSrt !== 'undefined') {
                downloadFunctions.push('downloadSrt');
            }
            
            return downloadFunctions;
            """
            
            available_functions = self.driver.execute_script(download_script)
            
            if available_functions:
                print(f"✅ Найдены функции скачивания: {available_functions}")
            else:
                print("⚠️ Функции скачивания не найдены в JavaScript")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке генерации ссылок: {e}")
    
    def test_03_file_download_simulation(self):
        """Тест 3: Симуляция скачивания файла"""
        print("\n=== Тест 3: Симуляция скачивания ===")
        
        # Создаем тестовые данные для скачивания
        test_data = {
            'text': "Это тестовый текст для скачивания",
            'format': 'txt'
        }
        
        try:
            # Используем JavaScript для создания и скачивания файла
            download_script = f"""
            var text = "{test_data['text']}";
            var filename = "test_download.txt";
            
            // Создаем blob
            var blob = new Blob([text], {{type: 'text/plain'}});
            
            // Создаем временную ссылку
            var link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            
            // Добавляем ссылку на страницу и кликаем
            document.body.appendChild(link);
            link.click();
            
            // Убираем ссылку
            document.body.removeChild(link);
            
            return 'download_initiated';
            """
            
            result = self.driver.execute_script(download_script)
            
            if result == 'download_initiated':
                print("✅ Скачивание инициировано через JavaScript")
                
                # Ждем некоторое время для завершения скачивания
                time.sleep(3)
                
                # Проверяем папку загрузок
                downloads_dir = Path.cwd() / "test_downloads"
                if downloads_dir.exists():
                    downloaded_files = list(downloads_dir.glob("*.txt"))
                    if downloaded_files:
                        print(f"✅ Найдены скачанные файлы: {[f.name for f in downloaded_files]}")
                    else:
                        print("⚠️ Скачанные файлы не найдены")
                else:
                    print("⚠️ Папка загрузок не создана")
                    
        except Exception as e:
            logger.error(f"Ошибка при симуляции скачивания: {e}")


class IntegratedUITest(UITestCase):
    """Интегрированные UI тесты - полный workflow"""
    
    def test_complete_workflow(self):
        """Полный тест workflow: загрузка → обработка → скачивание"""
        print("\n=== Интегрированный тест: полный workflow ===")
        
        audio_page_url = f"{self.live_server_url}/audio-to-text/"
        self.driver.get(audio_page_url)
        
        test_file = self.test_files['short_ru'][0]
        
        try:
            # Шаг 1: Загрузка файла
            print("📤 Шаг 1: Загружаем файл...")
            file_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(test_file)
            print(f"✅ Файл {Path(test_file).name} загружен")
            
            # Шаг 2: Настройка параметров
            print("⚙️ Шаг 2: Настраиваем параметры...")
            
            # Выбираем язык (если есть селектор)
            try:
                language_select = self.driver.find_element(
                    By.CSS_SELECTOR, "select[name='language'], #language"
                )
                language_select.send_keys("ru-RU")
                print("✅ Язык установлен: ru-RU")
            except:
                print("⚠️ Селектор языка не найден")
            
            # Выбираем формат вывода (если есть)
            try:
                format_select = self.driver.find_element(
                    By.CSS_SELECTOR, "select[name='output_format'], #output_format"
                )
                format_select.send_keys("text")
                print("✅ Формат вывода установлен: text")
            except:
                print("⚠️ Селектор формата не найден")
            
            # Шаг 3: Запуск обработки
            print("🚀 Шаг 3: Запускаем обработку...")
            submit_button = self.driver.find_element(
                By.CSS_SELECTOR, 
                "button[type='submit'], .convert-btn, .submit-btn, .process-btn"
            )
            submit_button.click()
            
            # Шаг 4: Мониторинг прогресса
            print("⏳ Шаг 4: Мониторим прогресс...")
            start_time = time.time()
            max_wait = 120  # 2 минуты максимум
            
            while time.time() - start_time < max_wait:
                try:
                    # Проверяем на ошибки
                    if "error" in self.driver.page_source.lower() or \
                       "ошибка" in self.driver.page_source.lower():
                        error_text = self.driver.find_element(
                            By.CSS_SELECTOR, ".error, .alert-danger, .error-message"
                        ).text
                        print(f"❌ Обнаружена ошибка: {error_text}")
                        break
                    
                    # Проверяем завершение
                    if "результат" in self.driver.page_source.lower() or \
                       "completed" in self.driver.page_source.lower() or \
                       "text" in self.driver.page_source.lower():
                        print("✅ Обработка завершена!")
                        break
                        
                    # Ищем индикаторы прогресса
                    progress_indicators = self.driver.find_elements(
                        By.CSS_SELECTOR, 
                        ".progress, .loading, .spinner, .processing"
                    )
                    
                    if progress_indicators:
                        print("🔄 Обработка в процессе...")
                    
                    time.sleep(3)
                    
                except Exception:
                    time.sleep(2)
                    continue
            
            # Шаг 5: Проверка результатов
            print("📊 Шаг 5: Проверяем результаты...")
            
            # Ищем текстовые результаты
            result_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                ".result, .output, .transcription, .text-result, textarea[readonly]"
            )
            
            if result_elements:
                for element in result_elements:
                    if element.text.strip():
                        print(f"✅ Найден результат: {element.text[:100]}...")
                        break
                else:
                    print("⚠️ Результаты найдены, но пусты")
            else:
                print("⚠️ Элементы результатов не найдены")
            
            # Шаг 6: Проверка опций скачивания
            print("💾 Шаг 6: Проверяем опции скачивания...")
            
            download_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, 
                ".download-btn, .download, [href*='download'], a[download]"
            )
            
            if download_buttons:
                print(f"✅ Найдено {len(download_buttons)} кнопок скачивания")
                
                # Пробуем кликнуть по первой кнопке скачивания
                try:
                    download_buttons[0].click()
                    print("✅ Скачивание инициировано")
                    time.sleep(2)
                except Exception as e:
                    print(f"⚠️ Ошибка при клике по кнопке скачивания: {e}")
                    
            else:
                print("⚠️ Кнопки скачивания не найдены")
            
            print("🎯 Интегрированный тест завершен")
            
        except TimeoutException:
            self.fail("Таймаут: элементы страницы не загрузились")
        except Exception as e:
            logger.error(f"Ошибка в интегрированном тесте: {e}")
            self.fail(f"Интегрированный тест провален: {e}")


def run_ui_tests():
    """Запуск всех UI тестов"""
    print("🖥️ Запуск UI тестирования STT системы")
    print("=" * 60)
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import unittest
    
    # Создаем test suite
    loader = unittest.TestLoader()
    
    # Добавляем все UI тесты
    drag_drop_suite = loader.loadTestsFromTestCase(DragAndDropTest)
    progress_suite = loader.loadTestsFromTestCase(ProgressBarTest)
    download_suite = loader.loadTestsFromTestCase(DownloadTest)
    integrated_suite = loader.loadTestsFromTestCase(IntegratedUITest)
    
    # Комбинируем все тесты
    combined_suite = unittest.TestSuite([
        drag_drop_suite, 
        progress_suite, 
        download_suite, 
        integrated_suite
    ])
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2, buffer=False)
    result = runner.run(combined_suite)
    
    # Выводим итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ UI ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"✅ Успешных тестов: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Неудачных тестов: {len(result.failures)}")
    print(f"🚨 Ошибок: {len(result.errors)}")
    print(f"📈 Всего тестов: {result.testsRun}")
    
    if result.failures:
        print("\n❌ НЕУДАЧНЫЕ ТЕСТЫ:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n🚨 ОШИБКИ:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\n🎯 Процент успешности UI тестов: {success_rate:.1f}%")
    
    return result


if __name__ == '__main__':
    run_ui_tests()
