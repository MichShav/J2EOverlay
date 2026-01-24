#!/bin/bash
# Installation script for J2EOverlay on Linux

echo "================================"
echo "J2EOverlay Installation Script"
echo "================================"
echo ""

# Check Python version
echo "[1/5] Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check for Tesseract
echo ""
echo "[2/5] Checking for Tesseract OCR..."
if ! command -v tesseract &> /dev/null; then
    echo "Tesseract OCR is not installed."
    echo "Installing Tesseract with Japanese language support..."

    # Detect package manager and install
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr tesseract-ocr-jpn
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y tesseract tesseract-langpack-jpn
    elif command -v pacman &> /dev/null; then
        sudo pacman -S tesseract tesseract-data-jpn
    else
        echo "Could not detect package manager. Please install Tesseract manually."
        exit 1
    fi
else
    echo "Tesseract OCR is already installed: $(tesseract --version | head -n 1)"
fi

# Create virtual environment
echo ""
echo "[3/5] Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Error creating virtual environment"
    exit 1
fi

# Activate virtual environment
echo ""
echo "[4/5] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "[5/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error installing dependencies"
    exit 1
fi

echo ""
echo "================================"
echo "Installation complete!"
echo "================================"
echo ""
echo "To run J2EOverlay:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run application: python main.py"
echo ""
echo "Or use the launcher script: ./run.sh"
