# J2EOverlay - Japanese to English Overlay Translator

A transparent overlay application that translates Japanese text to English in real-time. Designed for Japanese games and applications, works with fullscreen apps on Windows 7+ and Linux.

## Features

- **Real-time OCR**: Extracts Japanese text from screen using Tesseract OCR
- **Offline Translation**: Translates Japanese to English using local AI models (no internet required)
- **Game-Optimized**: Uses models specifically tuned for Japanese game text translation
- **Transparent Overlay**: Displays translations on top of original text with click-through support
- **Fullscreen Compatible**: Works with fullscreen games and applications
- **Cross-Platform**: Supports Windows 7+ and Linux
- **Region Selection**: Capture specific screen regions
- **Auto-Capture Mode**: Automatically scan and translate at intervals
- **System Tray**: Minimal interface, runs in background
- **Fast Translation**: ~200-400ms per translation on CPU, faster with GPU

## Requirements

- Python 3.7 or higher
- Tesseract OCR 4.0 or higher with Japanese language data
- ~1GB disk space for translation models
- Internet connection (one-time only, for downloading models)

## Installation

### 1. Install Tesseract OCR

#### Windows

Download and install Tesseract OCR from:
https://github.com/UB-Mannheim/tesseract/wiki

During installation, make sure to:
1. Install to default location (C:\Program Files\Tesseract-OCR)
2. Select "Additional language data" and check Japanese (jpn)

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-jpn
```

#### Linux (Fedora/RHEL)

```bash
sudo dnf install tesseract tesseract-langpack-jpn
```

### 2. Clone Repository

```bash
git clone https://github.com/MichShav/J2EOverlay.git
cd J2EOverlay
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or using a virtual environment (recommended):

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Download Translation Models

**IMPORTANT**: This is a one-time download (~400MB) and requires internet connection. After download, the app works completely offline.

```bash
python download_models.py
```

This will download:
- **Primary**: staka/fugumt-ja-en (game-optimized Japanese-English model)
- **Fallback**: Helsinki-NLP/opus-mt-ja-en (if primary fails)

The models are cached locally in your user directory and only need to be downloaded once.

## Usage

### Starting the Application

```bash
python main.py
```

The application will start in the system tray. The translation model loads in the background — a tray notification appears when it's ready. For verbose logs (useful for bug reports), run `python main.py --debug`.

### Basic Workflow

1. **Select Capture Region** (Optional)
   - Right-click system tray icon → "Select Region"
   - Click and drag to select the area containing Japanese text
   - Press ESC to cancel

2. **Capture and Translate**
   - Right-click system tray icon → "Capture & Translate"
   - Or use hotkey: `Ctrl+Shift+T` (configurable)

3. **View Translation**
   - Translation appears as overlay on top of original text
   - Toggle overlay visibility: `Ctrl+Shift+O`

4. **Auto-Capture Mode**
   - Right-click system tray icon → "Enable Auto-Capture"
   - Automatically scans and translates at set intervals
   - Useful for games with dialogue

### System Tray Menu

- **Select Region**: Choose specific screen area to capture
- **Clear Region**: Reset to full screen capture
- **Capture & Translate**: Perform one-time capture and translation
- **Toggle Overlay**: Show/hide translation overlay
- **Enable Auto-Capture**: Toggle automatic scanning mode
- **Quit**: Exit application

### Hotkeys (Default)

- `Ctrl+Shift+T`: Capture and translate
- `Ctrl+Shift+O`: Toggle overlay visibility
- `Ctrl+Shift+Q`: Quit application

*Hotkeys can be customized in config.json*

## Configuration

Edit `config.json` to customize settings:

### OCR Settings

```json
"ocr": {
  "language": "jpn",
  "tesseract_path": "",
  "confidence_threshold": 60,
  "psm": 6,
  "upscale": 2
}
```

- `language`: OCR language (`jpn` for Japanese; use `jpn+jpn_vert` to also detect vertical text)
- `tesseract_path`: Custom Tesseract executable path (leave empty for auto-detect)
- `confidence_threshold`: Minimum OCR confidence (0-100)
- `psm`: Tesseract page segmentation mode (`6` = uniform block, best for a selected dialogue region; `11` = sparse text, better for full-screen capture)
- `upscale`: Upscale factor applied before OCR (game text is usually too small for Tesseract at native size)

### Translation Settings

```json
"translation": {
  "source_lang": "ja",
  "target_lang": "en",
  "model_path": "",
  "fp16": false
}
```

- `source_lang`: Source language code (ja = Japanese)
- `target_lang`: Target language code (en = English)
- `model_path`: Custom model path (leave empty to use default downloaded models)
- `fp16`: Run the model in half precision on GPU (faster, but can occasionally produce blank translations on some hardware — leave off unless you need the speed)

### Overlay Appearance

```json
"overlay": {
  "font_size": 14,
  "font_family": "Arial",
  "text_color": "#FFFFFF",
  "background_color": "#000000",
  "background_opacity": 0.7,
  "border_color": "#00FF00",
  "border_width": 2,
  "padding": 10
}
```

Customize colors, fonts, and transparency to your preference.

### Auto-Capture Settings

```json
"capture": {
  "scan_interval": 1000
}
```

- `scan_interval`: Milliseconds between auto-captures (1000 = 1 second)

## Fullscreen Game Support

### Windows

The overlay uses `Qt.WindowStaysOnTopHint` and `Qt.WindowTransparentForInput` flags to stay on top of fullscreen applications while remaining click-through.

**For some games**, you may need to run in windowed borderless mode:
- Set game to windowed mode
- Use the native resolution

### Linux

Works with both X11 and Wayland:
- **X11**: Full support for all features
- **Wayland**: May require additional permissions

For X11, ensure your window manager allows always-on-top windows.

## Troubleshooting

### "Tesseract not found" error

**Windows:**
- Verify Tesseract is installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Or set custom path in config.json: `"tesseract_path": "C:\\path\\to\\tesseract.exe"`

**Linux:**
```bash
which tesseract
# Should return path like /usr/bin/tesseract
```

### No text detected

- Ensure Japanese language data is installed for Tesseract
- Check OCR confidence threshold in config.json (try lowering to 50)
- Verify the captured region contains clear, readable text
- Try increasing font size in game settings

### Translation not working

- Ensure translation models were downloaded (run `python download_models.py`)
- Check console output for model loading errors
- Verify sufficient disk space (~1GB needed)
- For GPU acceleration: Ensure CUDA is installed and compatible with PyTorch
- Try restarting the application after model download

### Overlay not visible in fullscreen

**Windows:**
- Try running game in windowed borderless mode
- Some games require DirectX/OpenGL overlays - may not work with all games

**Linux:**
- Check compositor settings
- Try different window manager if using a tiling WM

### High CPU usage

- Reduce auto-capture scan interval in config.json
- Use region selection to capture smaller area
- Disable auto-capture when not needed

## Performance Tips

1. **Use GPU acceleration** - If you have an NVIDIA GPU, install CUDA for 2-4x faster translation
2. **Select specific regions** instead of full screen
3. **Increase scan interval** for auto-capture (2000-3000ms recommended for games)
4. **Lower confidence threshold** only if needed
5. **Close other applications** for better performance

### GPU Acceleration (Optional)

For faster translation (~100-200ms instead of 200-400ms):

1. Install NVIDIA CUDA Toolkit (11.8 or newer)
2. Install PyTorch with CUDA support:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```
3. Restart J2EOverlay - it will automatically use GPU if available

## Platform-Specific Notes

### Windows 7

- Requires Python 3.7 or 3.8 (newer versions may not support Win7)
- Ensure Windows Aero is enabled for transparency effects
- May need to run as administrator for some games

### Linux

- Tested on Ubuntu 20.04+, Fedora 34+, Arch Linux
- Works with GNOME, KDE, XFCE, i3
- Wayland support is experimental

## Development

### Project Structure

```
J2EOverlay/
├── main.py              # Application entry point
├── config.json          # Configuration file
├── requirements.txt     # Python dependencies
├── src/
│   ├── __init__.py
│   ├── config.py        # Configuration manager
│   ├── pipeline.py      # Background worker (capture -> OCR -> translate)
│   ├── screen_capture.py # Screen capture module
│   ├── ocr_engine.py    # OCR processing
│   ├── translator.py    # Translation service
│   └── overlay.py       # Overlay window UI
└── README.md
```

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - feel free to use and modify.

## Acknowledgments

- Tesseract OCR for text recognition
- FuguMT (staka) and Helsinki-NLP OPUS-MT for translation models
- Hugging Face Transformers for model inference
- PyQt5 for GUI framework
- mss for screen capture

## Support

For issues and questions:
- GitHub Issues: https://github.com/MichShav/J2EOverlay/issues
- Discussions: https://github.com/MichShav/J2EOverlay/discussions

## Roadmap

- [x] Offline translation with local models
- [ ] Support for additional translation services (DeepL, Azure)
- [ ] manga-ocr backend for stylized game fonts
- [ ] Multiple language support
- [ ] Custom dictionary/glossary
- [ ] Translation history
- [ ] Improved text detection algorithms
- [ ] macOS support
