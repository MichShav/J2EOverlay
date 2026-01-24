@echo off
REM Launcher script for J2EOverlay on Windows

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment and run
call venv\Scripts\activate.bat
python main.py
