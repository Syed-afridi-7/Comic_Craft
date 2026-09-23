@echo off
setlocal enabledelayedexpansion
title ComicCraft - AI Comic Story Creator

echo ========================================================
echo         ComicCraft: AI Comic Story Creator
echo ========================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo and ensure "Add Python to PATH" is checked.
    echo.
    pause
    exit /b 1
)

:: 2. Check and activate virtual environment if present
if exist "env\Scripts\activate.bat" (
    echo [*] Activating virtual environment 'env'...
    call env\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment 'venv'...
    call venv\Scripts\activate.bat
) else (
    echo [*] Using system Python environment.
)

:: 3. Check for .env file
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Creating .env from .env.example with default mock/offline settings...
        copy .env.example .env >nul
    )
)

:: 4. Verify/Ensure required directories exist
if not exist "static\panels" mkdir "static\panels"
if not exist "static\exports" mkdir "static\exports"

echo.
echo [*] Starting ComicCraft server on http://127.0.0.1:8000
echo [*] Press CTRL+C in this window to stop the server.
echo.

:: 5. Open default browser after a 2-second delay
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

:: 6. Launch Uvicorn ASGI Server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

if %errorlevel% neq 0 (
    echo.
    echo [!] Server exited with an error.
    echo If dependencies are missing, run: pip install -r requirements.txt
    echo.
    pause
)
