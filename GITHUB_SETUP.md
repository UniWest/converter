# 🐙 Загрузка проекта на GitHub

## 📋 Пошаговая инструкция

### Вариант 1: Через веб-интерфейс GitHub (проще)

#### 1. Создайте новый репозиторий
1. Перейдите на https://github.com
2. Войдите в аккаунт или зарегистрируйтесь
3. Нажмите **"+"** → **"New repository"**
4. Заполните форму:
   - **Repository name:** `video-to-gif-converter`
   - **Description:** `🎬➡️📸 Django web app for converting videos to animated GIFs`
   - **Public** ✅ (или Private, если хотите)
   - **Add a README file** ❌ (у нас уже есть)
   - **Add .gitignore** ❌ (у нас уже есть)
   - **Choose a license** ❌ (у нас уже есть MIT)
5. Нажмите **"Create repository"**

#### 2. Загрузите файлы
1. На странице нового репозитория нажмите **"uploading an existing file"**
2. Перетащите ВСЕ файлы из папки `C:\Users\aksen\Downloads\сайт\`
3. Или нажмите **"choose your files"** и выберите все файлы
4. В поле "Commit changes" введите: `Initial commit - Video to GIF Converter`
5. Нажмите **"Commit changes"**

### Вариант 2: Через Git (нужно установить Git)

#### 1. Установите Git
- Скачайте с https://git-scm.com/download/win
- Установите с настройками по умолчанию

#### 2. Настройте Git (выполните в PowerShell)
```bash
git config --global user.name "Ваше Имя"
git config --global user.email "ваш-email@example.com"
```

#### 3. Создайте репозиторий на GitHub (как в Варианте 1)

#### 4. Загрузите код
```bash
# В папке проекта C:\Users\aksen\Downloads\сайт\
git init
git add .
git commit -m "Initial commit - Video to GIF Converter"
git branch -M main
git remote add origin https://github.com/ВАШЕ_ИМЯ/video-to-gif-converter.git
git push -u origin main
```

## 🔗 После загрузки

### Обновите ссылки в README.md
1. Замените `yourusername` на ваше GitHub имя
2. Замените `your.email@example.com` на ваш email
3. Добавьте реальные скриншоты (загрузите в Issues → New Issue → вставьте изображение)

### Настройте GitHub Pages (опционально)
1. В настройках репозитория → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main**
4. Ваш сайт будет доступен по адресу: `https://ваше-имя.github.io/video-to-gif-converter`

## 🚀 Клонирование для других разработчиков

Теперь другие могут клонировать проект:
```bash
git clone https://github.com/ваше-имя/video-to-gif-converter.git
cd video-to-gif-converter
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## 📦 Готовые файлы для GitHub

В вашей папке уже есть все необходимое:

- ✅ **README.md** - описание проекта
- ✅ **LICENSE** - MIT лицензия  
- ✅ **.gitignore** - исключения из версионирования
- ✅ **requirements.txt** - зависимости Python
- ✅ **PYTHONANYWHERE_DEPLOY.md** - инструкция по деплою
- ✅ **Весь код проекта** - готов к загрузке

## 🎯 Рекомендуемые настройки репозитория

После создания зайдите в **Settings** репозитория и настройте:

### General
- **Features:** Issues ✅, Wiki ❌, Sponsorships ❌
- **Pull Requests:** Allow merge commits ✅

### Branches  
- **Branch protection rule** для `main`:
  - Require pull request reviews ✅
  - Dismiss stale reviews ✅

### Pages
- **Source:** Deploy from a branch
- **Branch:** main / (root)

## 🏷️ Добавьте topics (теги)

В разделе **About** добавьте topics:
- `django`
- `python`  
- `video-converter`
- `gif-maker`
- `web-application`
- `moviepy`
- `ffmpeg`

## 📊 Badges для README

Добавьте красивые badges:
```markdown
![GitHub stars](https://img.shields.io/github/stars/yourusername/video-to-gif-converter)
![GitHub forks](https://img.shields.io/github/forks/yourusername/video-to-gif-converter)
![GitHub issues](https://img.shields.io/github/issues/yourusername/video-to-gif-converter)
```

---

**Готово! Ваш проект теперь доступен всему миру! 🌍**
