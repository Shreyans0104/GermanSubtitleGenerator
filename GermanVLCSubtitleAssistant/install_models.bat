@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run setup_online.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python install_models.py
if errorlevel 1 (
  echo Model installation failed. Check the internet connection and disk space.
  pause
  exit /b 1
)
pause
