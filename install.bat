@echo off
REM Installation script for J2EOverlay on Windows

echo ================================
echo J2EOverlay Installation Script
echo ================================
echo.

REM Check Python version
echo [1/4] Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check for Tesseract
echo.
echo [2/4] Checking for Tesseract OCR...
where tesseract >nul 2>&1
if %errorlevel% neq 0 (
    echo Tesseract OCR is not installed or not in PATH.
    echo Please install Tesseract from:
    echo https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo Make sure to:
    echo   1. Install Japanese language data ^(jpn^)
    echo   2. Add Tesseract to PATH or install to default location
    echo.
    pause
    exit /b 1
) else (
    tesseract --version
)

REM Create virtual environment
echo.
echo [3/4] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo Error creating virtual environment
    pause
    exit /b 1
)

REM Activate and install dependencies
echo.
echo [4/4] Installing Python dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies
    pause
    exit /b 1
)

echo.
echo ================================
echo Installation complete!
echo ================================
echo.
echo To run J2EOverlay:
echo   1. Double-click run.bat
echo   or
echo   2. Run manually:
echo      venv\Scripts\activate.bat
echo      python main.py
echo.
pause
