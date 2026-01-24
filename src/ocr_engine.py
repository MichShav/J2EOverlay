"""OCR engine for Japanese text recognition"""

import pytesseract
from PIL import Image
import platform
import os
from typing import Optional, List, Dict


class OCREngine:
    """Handles OCR operations for Japanese text extraction"""

    def __init__(self, language: str = "jpn", tesseract_path: str = ""):
        self.language = language
        self._setup_tesseract(tesseract_path)

    def _setup_tesseract(self, custom_path: str) -> None:
        """Setup Tesseract OCR path based on platform"""
        if custom_path and os.path.exists(custom_path):
            pytesseract.pytesseract.tesseract_cmd = custom_path
        elif platform.system() == "Windows":
            # Common Windows installation paths
            possible_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break

    def extract_text(self, image: Image.Image, confidence_threshold: int = 60) -> Optional[str]:
        """
        Extract text from image using Tesseract OCR

        Args:
            image: PIL Image object
            confidence_threshold: Minimum confidence level (0-100)

        Returns:
            Extracted text or None if extraction fails
        """
        try:
            # Use Tesseract to extract text
            text = pytesseract.image_to_string(
                image,
                lang=self.language,
                config='--psm 6'  # Assume uniform block of text
            )
            return text.strip() if text else None
        except Exception as e:
            print(f"OCR error: {e}")
            return None

    def extract_text_with_boxes(self, image: Image.Image) -> List[Dict]:
        """
        Extract text with bounding box information

        Args:
            image: PIL Image object

        Returns:
            List of dictionaries containing text and position info
        """
        try:
            data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
                config='--psm 6'
            )

            results = []
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                if int(data['conf'][i]) > 0:  # Only include confident results
                    text = data['text'][i].strip()
                    if text:
                        results.append({
                            'text': text,
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'confidence': data['conf'][i]
                        })
            return results
        except Exception as e:
            print(f"OCR with boxes error: {e}")
            return []

    def is_japanese_text(self, text: str) -> bool:
        """
        Check if text contains Japanese characters

        Args:
            text: Text to check

        Returns:
            True if text contains Japanese characters
        """
        if not text:
            return False

        # Unicode ranges for Japanese characters
        for char in text:
            code = ord(char)
            # Hiragana: 3040-309F
            # Katakana: 30A0-30FF
            # Kanji: 4E00-9FFF
            if (0x3040 <= code <= 0x309F or
                0x30A0 <= code <= 0x30FF or
                0x4E00 <= code <= 0x9FFF):
                return True
        return False

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results

        Args:
            image: PIL Image object

        Returns:
            Preprocessed PIL Image
        """
        # Convert to grayscale
        image = image.convert('L')

        # Increase contrast (simple threshold)
        # This can be enhanced with more sophisticated preprocessing
        return image
