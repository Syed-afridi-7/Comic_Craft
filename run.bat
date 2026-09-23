@echo off
title ComicCraft - AI Comic Story Creator
cd /d "%~dp0"

echo ========================================================
echo         ComicCraft: AI Comic Story Creator
echo ========================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo and ensure "Add Python to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

if exist "env\Scripts\activate.bat" (
    echo [*] Activating virtual environment 'env'...
    call env\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment 'venv'...
    call venv\Scripts\activate.bat
)

python run.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Server stopped or exited with code %errorlevel%.
    echo If dependencies are missing, run: pip install -r requirements.txt
    echo.
    pause
)
