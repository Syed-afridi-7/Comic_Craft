@echo off
setlocal enabledelayedexpansion
title ComicCraft - AI Comic Story Creator

:: Change directory to where this batch file is located
cd /d "%~dp0"

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
        echo [*] Initializing .env from .env.example (mock/offline mode by default)...
        copy /y ".env.example" ".env" >nul
    )
)

:: 4. Verify/Ensure required media directories exist
if not exist "static\panels" mkdir "static\panels"
if not exist "static\exports" mkdir "static\exports"

:: 5. Check if port 8000 is already in use
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>nul
if %errorlevel% equ 0 (
    echo [!] Port 8000 is currently in use by another process.
    echo Attempting to free port 8000...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr /R /C:":8000 .*LISTENING"') do (
        echo Terminating process on port 8000 (PID: %%a)...
        taskkill /F /T /PID %%a >nul 2>nul
    )
    ping 127.0.0.1 -n 2 >nul
)

echo.
echo [*] Launching ComicCraft server...
echo [*] Access URLs:
echo       Web Studio: http://127.0.0.1:8000  (or http://localhost:8000)
echo       API Docs:   http://127.0.0.1:8000/docs
echo.
echo [*] Press CTRL+C in this window to stop the server.
echo.

:: 6. Open browser after a 2-second delay using ping (avoids timeout redirection errors)
start "" cmd /c "ping 127.0.0.1 -n 3 >nul && start http://127.0.0.1:8000"

:: 7. Launch Uvicorn ASGI Server bound to 0.0.0.0 (handles both 127.0.0.1 and localhost)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

if %errorlevel% neq 0 (
    echo.
    echo [!] Server stopped or exited with code %errorlevel%.
    echo If dependencies are missing, run: pip install -r requirements.txt
    echo.
    pause
)
