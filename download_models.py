#!/usr/bin/env python3
"""
Model downloader for J2EOverlay
Downloads the offline translation models
"""

import argparse
import sys


def download_translation_model():
    """Download the offline Japanese-English translation model"""
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        # Single source of truth for model names, shared with the app
        from src.translator import PRIMARY_MODEL, FALLBACK_MODEL

        print("=" * 60)
        print("J2EOverlay - Model Downloader")
        print("=" * 60)
        print()

        # Try game-optimized model first
        model_name = PRIMARY_MODEL
        print(f"Downloading game-optimized translation model: {model_name}")
        print("This is a ~400MB download and may take several minutes...")
        print()

        try:
            print("Downloading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            print("✓ Tokenizer downloaded")

            print("Downloading translation model...")
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            print("✓ Translation model downloaded")

            print()
            print("=" * 60)
            print("✓ Model download complete!")
            print("=" * 60)
            print()
            print("Model cached and ready for offline use.")
            print("You can now run J2EOverlay without internet connection.")

        except Exception as e:
            print(f"Failed to download {model_name}: {e}")
            print()
            print("Falling back to Helsinki-NLP opus-mt-ja-en model...")

            model_name = FALLBACK_MODEL
            print(f"Downloading: {model_name}")
            print("This is a ~300MB download...")
            print()

            print("Downloading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            print("✓ Tokenizer downloaded")

            print("Downloading translation model...")
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            print("✓ Translation model downloaded")

            print()
            print("=" * 60)
            print("✓ Fallback model download complete!")
            print("=" * 60)
            print()
            print("Model cached and ready for offline use.")

        return True

    except ImportError:
        print("ERROR: Required libraries not installed!")
        print("Please install dependencies first:")
        print("  pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"ERROR: Failed to download model: {e}")
        import traceback
        traceback.print_exc()
        return False


def download_tesseract_data():
    """Provide instructions for Tesseract language data"""
    print()
    print("=" * 60)
    print("Tesseract OCR Language Data")
    print("=" * 60)
    print()
    print("Tesseract requires Japanese language data (jpn.traineddata)")
    print()
    print("Windows:")
    print("  1. Download Tesseract installer from:")
    print("     https://github.com/UB-Mannheim/tesseract/wiki")
    print("  2. During installation, select 'Japanese' language data")
    print()
    print("Linux (Ubuntu/Debian):")
    print("  sudo apt-get install tesseract-ocr-jpn")
    print()
    print("Linux (Fedora/RHEL):")
    print("  sudo dnf install tesseract-langpack-jpn")
    print()
    print("macOS:")
    print("  brew install tesseract-lang")
    print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="J2EOverlay model downloader")
    parser.add_argument("-y", "--yes", action="store_true",
                        help="Skip the confirmation prompt (for scripted installs)")
    args = parser.parse_args()

    print()
    print("J2EOverlay - First-time Setup")
    print()
    print("This script will download the required translation models.")
    print("These models will be cached locally for offline use.")
    print()

    if not args.yes:
        response = input("Continue? (y/n): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Setup cancelled.")
            return

    print()

    # Download translation model
    success = download_translation_model()

    if success:
        # Show Tesseract info
        download_tesseract_data()

        print()
        print("=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Ensure Tesseract OCR with Japanese data is installed")
        print("  2. Run J2EOverlay: python main.py")
        print()
    else:
        print()
        print("Setup failed. Please check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
