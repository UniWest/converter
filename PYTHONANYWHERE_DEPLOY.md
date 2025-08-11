# 🐍 Деплой Django проекта на PythonAnywhere

## 📋 Пошаговая инструкция

### 1. Регистрация на PythonAnywhere
1. Перейдите на https://www.pythonanywhere.com/
2. Нажмите **"Pricing & signup"**
3. Выберите **"Create a Beginner account"** (БЕСПЛАТНО)
4. Зарегистрируйтесь с вашим email

### 2. Загрузка файлов проекта

#### Вариант A: Через веб-интерфейс Files
1. Войдите в **Dashboard** → **Files**
2. Перейдите в папку `/home/yourusername/`
3. Создайте папку `mysite`
4. Загрузите все файлы проекта в `mysite/`

#### Вариант B: Через Git (рекомендуется)
1. Создайте репозиторий на GitHub с вашими файлами
2. В **Console** на PythonAnywhere выполните:
```bash
cd ~
git clone https://github.com/yourusername/your-repo.git mysite
```

### 3. Установка зависимостей
В **Console** выполните:
```bash
cd ~/mysite
pip3.10 install --user -r requirements.txt
```

### 4. Настройка базы данных
```bash
cd ~/mysite
python3.10 manage.py migrate
python3.10 manage.py collectstatic --noinput
```

### 5. Настройка Web App
1. Перейдите в **Dashboard** → **Web**
2. Нажмите **"Add a new web app"**
3. Выберите домен: `yourusername.pythonanywhere.com`
4. Выберите **"Manual configuration"**
5. Выберите **Python 3.10**

### 6. Конфигурация WSGI
1. В разделе **Code** найдите **"WSGI configuration file"**
2. Нажмите на ссылку (например: `/var/www/yourusername_pythonanywhere_com_wsgi.py`)
3. Замените содержимое файла на:

```python
import os
import sys

# Add your project directory to sys.path
path = '/home/yourusername/mysite'  # ЗАМЕНИТЕ yourusername на ваш логин!
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'converter_site.settings'

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 7. Настройка статических файлов
1. В разделе **Static files** добавьте:
   - **URL:** `/static/`
   - **Directory:** `/home/yourusername/mysite/staticfiles/`

2. Добавьте еще одну запись:
   - **URL:** `/media/`
   - **Directory:** `/home/yourusername/mysite/media/`

### 8. Настройка переменных окружения
1. В разделе **Environment variables** добавьте:
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `yourusername.pythonanywhere.com`
   - `SECRET_KEY` = `your-secret-key-here`

### 9. Обновление настроек
В файле `.env` замените:
```
ALLOWED_HOSTS=yourusername.pythonanywhere.com,localhost,127.0.0.1
```
На ваш реальный домен PythonAnywhere.

### 10. Перезапуск приложения
1. Нажмите зеленую кнопку **"Reload yourusername.pythonanywhere.com"**
2. Подождите несколько секунд
3. Перейдите на ваш сайт: `https://yourusername.pythonanywhere.com`

## 🔧 Решение проблем

### Проблема: Ошибка импорта модулей
**Решение:** Убедитесь, что путь в WSGI файле правильный:
```python
path = '/home/ВАШЕ_ИМЯ_ПОЛЬЗОВАТЕЛЯ/mysite'
```

### Проблема: Статические файлы не загружаются
**Решение:** Выполните в консоли:
```bash
cd ~/mysite
python3.10 manage.py collectstatic --noinput
```

### Проблема: FFmpeg не работает
**Решение:** На PythonAnywhere FFmpeg не установлен по умолчанию. Нужно:
1. Изменить `converter/utils.py` чтобы использовать только MoviePy
2. Или отключить функции, требующие FFmpeg

### Проблема: Превышение лимитов памяти
**Решение:** 
1. Уменьшите максимальный размер загружаемых файлов
2. Оптимизируйте обработку видео

## 📊 Лимиты бесплатного аккаунта
- **CPU секунды:** 100 в день
- **Хранилище:** 512MB
- **Один веб-сайт**
- **Нет HTTPS** (только HTTP)

## 🔄 Обновление кода
При изменении кода:
1. Загрузите новые файлы через **Files** или `git pull`
2. При необходимости выполните `python3.10 manage.py migrate`
3. Выполните `python3.10 manage.py collectstatic --noinput`
4. Нажмите **"Reload"** в разделе Web

## 📞 Поддержка
- **Документация:** https://help.pythonanywhere.com/
- **Форум:** https://www.pythonanywhere.com/forums/
- **Ошибки в логах:** Dashboard → Tasks → Error log

---

**Удачи с деплоем! 🚀**
