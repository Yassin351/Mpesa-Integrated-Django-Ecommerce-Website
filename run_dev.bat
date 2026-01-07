@echo off
setlocal enabledelayedexpansion

REM Change to the directory of this script
cd /d "%~dp0"

REM Check for Python
where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python is not installed or not in PATH.
  echo Install Python 3.x from https://www.python.org/downloads/ and ensure "Add Python to PATH" is checked.
  pause
  exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
  )
)

REM Upgrade pip
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip.
  pause
  exit /b 1
)

REM Install dependencies
if exist "requirements.txt" (
  echo [INFO] Installing dependencies from requirements.txt ...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
  )
) else (
  echo [WARN] requirements.txt not found. Skipping dependency installation.
)

REM Set environment variables for development
set DJANGO_DEBUG=True
set DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
set DJANGO_SECRET_KEY=dev-secret-change-me

REM Apply migrations
echo [INFO] Applying migrations...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 (
  echo [ERROR] Migrations failed.
  pause
  exit /b 1
)

REM Start server in a new window and open browser
set PORT=8000
set URL=http://127.0.0.1:%PORT%/

echo [INFO] Launching Django development server in a new window...
start "Django Dev Server" cmd /k ""%CD%\.venv\Scripts\python.exe" manage.py runserver 127.0.0.1:%PORT%"

REM Give the server a couple seconds to start, then open browser
TIMEOUT /T 3 /NOBREAK >NUL
start "" "%URL%"

echo [INFO] If the page doesn't load, check the new server window for errors (e.g., port already in use, import errors, etc.).
echo [INFO] Press any key to close this helper window. The server will continue running in its own window.
PAUSE >NUL

endlocal
