@echo off
chcp 65001 >nul
cd /d "C:\Users\aksen\Downloads\сайт"
echo Current directory:
dir
echo.
echo Python version:
python --version
echo.
echo Starting Django server...
python manage.py runserver
echo.
echo Server stopped. Press any key to close...
pause >nul
