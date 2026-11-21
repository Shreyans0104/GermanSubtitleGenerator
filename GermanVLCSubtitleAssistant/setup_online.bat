@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.11 x64 from https://www.python.org/downloads/windows/
  echo During setup, check "Add Python to PATH".
  pause
  exit /b 1
)
py -3.11 -c "import sys; assert sys.version_info[:2] == (3,11), sys.version"
if errorlevel 1 (
  echo Python 3.11 was not found. Install Python 3.11 x64, then retry.
  pause
  exit /b 1
)
if not exist .venv py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip==25.2
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Review the error above.
  pause
  exit /b 1
)
echo.
echo Python dependencies installed.
echo Next: run install_models.bat while online to download speech and translation models.
pause
