@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run setup_online.bat and install_models.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
python app.py
if errorlevel 1 pause
