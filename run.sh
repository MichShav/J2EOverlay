#!/bin/bash
# Launcher script for J2EOverlay on Linux

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Please run install.sh first."
    exit 1
fi

# Run application
python main.py
