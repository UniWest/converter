#!/usr/bin/env python3
import os
import tempfile
from typing import Dict, List, Any
"""
Генератор тестовых аудиофайлов для проверки функции Speech-to-Text
"""

from pathlib import Path
import logging
from pydub import AudioSegment
from pydub.generators import Sine

logger = logging.getLogger(__name__)


class TestAudioGenerator:
    """Генератор тестовых аудиофайлов для STT тестирования"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent / "test_audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Тестовые фразы на разных языках
        self.test_phrases = {
            'ru': [
                "Привет мир, это тест распознавания русской речи",
                "Сегодня хорошая погода для тестирования",
                "Искусственный интеллект развивается очень быстро",
                "Число пи равно три целых четырнадцать сотых",
                "Москва столица России с населением более двенадцати миллионов человек"
            ],
            'en': [
                "Hello world, this is a test of English speech recognition",
                "Today is a good day for testing our system",
                "Artificial intelligence is developing very quickly",
                "The number pi equals three point fourteen",
                "London is the capital of the United Kingdom"
            ]
        }
        
        # Предустановленные настройки качества
        self.quality_presets = {
            'low': {
                'sample_rate': 8000,
                'bitrate': 64,
                'channels': 1
            },
            'medium': {
                'sample_rate': 16000,
                'bitrate': 128,
                'channels': 1
            },
            'high': {
                'sample_rate': 44100,
                'bitrate': 320,
                'channels': 2
            }
        }
    
    def generate_silence(self, duration_ms: int) -> AudioSegment:
        """Генерирует тишину заданной длительности"""
        return AudioSegment.silent(duration=duration_ms)
    
    def generate_tone(self, frequency: int = 440, duration_ms: int = 1000) -> AudioSegment:
        """Генерирует тон заданной частоты"""
        return Sine(frequency).to_audio_segment(duration=duration_ms)
    
    def create_test_audio_simple(self, duration_seconds: int = 15, language: str = 'ru') -> str:
        """
        Создает простой тестовый аудиофайл с синтезированными звуками
        для проверки основной функциональности
        """
        duration_ms = duration_seconds * 1000
        
        # Создаем базовый аудиосигнал из тонов разной частоты
        base_audio = AudioSegment.empty()
        
        # Добавляем тоны с паузами между ними
        frequencies = [440, 880, 1320, 660, 1100]  # A4, A5, E6, E5, C#6
        tone_duration = duration_ms // (len(frequencies) * 2)  # Делим время между тонами и паузами
        
        for freq in frequencies:
            base_audio += self.generate_tone(freq, tone_duration)
            base_audio += self.generate_silence(tone_duration // 2)
        
        # Нормализуем громкость
        base_audio = base_audio.normalize()
        
        # Добавляем метаданные
        filename = f"test_audio_{language}_{duration_seconds}s_simple.wav"
        output_path = self.output_dir / filename
        
        # Сохраняем в WAV формате
        base_audio.export(str(output_path), format="wav")
        
        logger.info(f"Создан тестовый аудиофайл: {output_path}")
        return str(output_path)
    
    def create_complex_test_audio(self, language: str = 'ru', duration_minutes: int = 5) -> str:
        """
        Создает более сложный тестовый файл для проверки сегментации и стабильности
        """
        total_duration_ms = duration_minutes * 60 * 1000
        segment_duration_ms = 10000  # 10-секундные сегменты
        
        complex_audio = AudioSegment.empty()
        current_position = 0
        
        # Создаем различные типы аудиосегментов
        segment_types = [
            'speech_simulation',
            'silence',
            'noise',
            'tone',
            'mixed'
        ]
        
        while current_position < total_duration_ms:
            remaining_time = min(segment_duration_ms, total_duration_ms - current_position)
            
            # Выбираем тип сегмента циклически
            segment_type = segment_types[len(complex_audio) // segment_duration_ms % len(segment_types)]
            
            if segment_type == 'speech_simulation':
                # Имитация речи через последовательность тонов разной частоты
                speech_sim = self._create_speech_simulation(remaining_time)
            elif segment_type == 'silence':
                speech_sim = self.generate_silence(remaining_time)
            elif segment_type == 'noise':
                speech_sim = self._create_white_noise(remaining_time)
            elif segment_type == 'tone':
                speech_sim = self.generate_tone(440 + (len(complex_audio) % 5) * 220, remaining_time)
            else:  # mixed
                speech_sim = self._create_mixed_segment(remaining_time)
            
            complex_audio += speech_sim
            current_position += remaining_time
        
        # Нормализуем и сохраняем
        complex_audio = complex_audio.normalize()
        
        filename = f"test_audio_{language}_{duration_minutes}min_complex.wav"
        output_path = self.output_dir / filename
        
        complex_audio.export(str(output_path), format="wav")
        
        logger.info(f"Создан сложный тестовый аудиофайл: {output_path} ({duration_minutes} мин)")
        return str(output_path)
    
    def _create_speech_simulation(self, duration_ms: int) -> AudioSegment:
        """Создает имитацию речи через модулированные тоны"""
        speech_audio = AudioSegment.empty()
        
        # Характерные частоты человеческой речи
        speech_frequencies = [250, 500, 1000, 2000, 4000, 8000]
        segment_duration = duration_ms // 20  # Короткие сегменты для имитации фонем
        
        for i in range(20):
            freq = speech_frequencies[i % len(speech_frequencies)]
            # Добавляем небольшие вариации частоты
            freq_variation = freq + (i % 3 - 1) * 50
            tone_segment = self.generate_tone(int(freq_variation), segment_duration)
            
            # Добавляем короткие паузы между "фонемами"
            if i % 4 == 0:  # Паузы между "словами"
                tone_segment += self.generate_silence(segment_duration // 4)
            
            speech_audio += tone_segment
        
        return speech_audio
    
    def _create_white_noise(self, duration_ms: int) -> AudioSegment:
        """Создает белый шум"""
        import random
        
        # Простейший белый шум через случайные значения
        samples = []
        sample_rate = 16000
        num_samples = int(duration_ms * sample_rate / 1000)
        
        for _ in range(num_samples):
            samples.append(random.randint(-32767, 32767))
        
        # Создаем AudioSegment из сырых данных
        noise = AudioSegment(
            data=b''.join([sample.to_bytes(2, 'little', signed=True) for sample in samples]),
            sample_width=2,
            frame_rate=sample_rate,
            channels=1
        )
        
        # Понижаем громкость шума
        return noise - 20  # -20 дБ
    
    def _create_mixed_segment(self, duration_ms: int) -> AudioSegment:
        """Создает смешанный сегмент из речи, тишины и тонов"""
        mixed = AudioSegment.empty()
        segment_length = duration_ms // 3
        
        # Речь
        mixed += self._create_speech_simulation(segment_length)
        # Тишина
        mixed += self.generate_silence(segment_length)
        # Тон
        mixed += self.generate_tone(660, segment_length)
        
        return mixed
    
    def create_test_suite(self) -> Dict[str, List[str]]:
        """
        Создает полный набор тестовых файлов согласно требованиям
        """
        test_files = {
            'short_ru': [],
            'short_en': [],
            'long_files': []
        }
        
        # 1. Короткие тест-клипы RU/EN (15-60 сек)
        for lang in ['ru', 'en']:
            for duration in [15, 30, 45, 60]:
                file_path = self.create_test_audio_simple(duration, lang)
                test_files[f'short_{lang}'].append(file_path)
        
        # 2. Длинные файлы 5-10 мин для проверки сегментации
        for duration_min in [5, 7, 10]:
            for lang in ['ru', 'en']:
                file_path = self.create_complex_test_audio(lang, duration_min)
                test_files['long_files'].append(file_path)
        
        # Сохраняем информацию о созданных файлах
        self._save_test_info(test_files)
        
        return test_files
    
    def _save_test_info(self, test_files: Dict[str, List[str]]):
        """Сохраняет информацию о созданных тестовых файлах"""
        import json
        from datetime import datetime
        
        test_info = {
            'created_at': datetime.now().isoformat(),
            'test_files': test_files,
            'total_files': sum(len(files) for files in test_files.values()),
            'output_directory': str(self.output_dir)
        }
        
        info_path = self.output_dir / 'test_info.json'
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(test_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Информация о тестах сохранена в {info_path}")


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Создание тестовых файлов
    generator = TestAudioGenerator()
    
    print("Создание тестовых аудиофайлов для STT...")
    test_files = generator.create_test_suite()
    
    print("\nСозданные файлы:")
    for category, files in test_files.items():
        print(f"\n{category}:")
        for file in files:
            print(f"  - {Path(file).name}")
    
    print(f"\nВсе тестовые файлы сохранены в: {generator.output_dir}")
