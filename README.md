# 🎬 Конвертер Медиафайлов

Полнофункциональное Django веб-приложение для конвертации медиафайлов с расширенными возможностями транскрибации аудио в текст (STT).

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Django](https://img.shields.io/badge/Django-5.2.5-green)
![Celery](https://img.shields.io/badge/Celery-5.4.0-green)
![License](https://img.shields.io/badge/License-Apache--2.0-yellow)

## 🚀 Возможности

### 📝 Speech-to-Text (STT)
- **Два движка транскрибации:**
  - 🔥 **faster-whisper** - локальная обработка, высокое качество
  - 🌐 **Google Speech Recognition** - онлайн API, быстрая обработка коротких файлов
- **Предобработка аудио:**
  - Нормализация громкости
  - Фильтрация частот (HP/LP фильтры)
  - Шумоподавление с помощью noisereduce
  - Сегментация по паузам через split_on_silence
- **Поддерживаемые форматы:** MP3, WAV, M4A, FLAC, OGG, AAC, WMA
- **Выходные форматы:** TXT, SRT (субтитры), JSON
- **Языки:** Русский, Английский, Испанский, Французский, Немецкий и другие

### 🎦 Видео в GIF
- Конвертация видео в анимированные GIF
- Настраиваемое качество и размер
- Эффекты: реверс, бумеранг, монохром

### 🖼️ Изображения в GIF
- Создание анимации из набора изображений
- Настраиваемая продолжительность кадров
- Эффекты пинг-понг и оптимизация

### ⚙️ Технологические особенности
- **Асинхронные задачи:** Celery + Redis
- **Мониторинг:** Flower для отслеживания задач
- **Docker:** Полная контейнеризация для развертывания
- **Переносимость:** Ничего дополнительно не нужно устанавливать

## 🚀 Быстрый старт

### Локальная установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/UniWest/converter.git
cd converter
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Настройте базу данных:**
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

5. **Запустите сервер:**
```bash
python manage.py runserver
```

6. **Откройте браузер:** http://localhost:8000

## 📋 Технические требования

- **Python:** 3.8+
- **Django:** 5.2.5
- **MoviePy:** для обработки видео
- **FFmpeg:** опционально, для расширенных возможностей
- **Pillow:** для работы с изображениями

## 📄 Лицензия

Этот проект лицензирован под Apache 2.0 License - см. файл [LICENSE](LICENSE) для подробностей.

## 👨‍💻 Автор

**UniWest**
- GitHub: [@UniWest](https://github.com/UniWest)

---

⭐ **Поставьте звезду, если проект был полезен!** ⭐
