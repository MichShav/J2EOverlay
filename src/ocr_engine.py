"""OCR engine for Japanese text recognition"""

import logging
import os
import platform
from collections import defaultdict
from typing import Optional, List, Dict

import pytesseract
from PIL import Image, ImageOps, ImageStat

logger = logging.getLogger(__name__)


class OCREngine:
    """Handles OCR operations for Japanese text extraction"""

    def __init__(self, language: str = "jpn", tesseract_path: str = "",
                 psm: int = 6, confidence_threshold: int = 60,
                 upscale: int = 2):
        """
        Args:
            language: Tesseract language code(s), e.g. "jpn" or "jpn+jpn_vert"
            tesseract_path: Custom Tesseract executable path
            psm: Page segmentation mode (6 = uniform block, good for a
                 selected dialogue region; 11 = sparse text, better for
                 full-screen capture)
            confidence_threshold: Minimum word confidence (0-100)
            upscale: Integer upscale factor applied before OCR. Game text
                 is usually too small for Tesseract at native size.
        """
        self.language = language
        self.psm = psm
        self.confidence_threshold = confidence_threshold
        self.upscale = max(1, int(upscale))
        self._setup_tesseract(tesseract_path)

    def _setup_tesseract(self, custom_path: str) -> None:
        """Setup Tesseract OCR path based on platform"""
        if custom_path and os.path.exists(custom_path):
            pytesseract.pytesseract.tesseract_cmd = custom_path
        elif platform.system() == "Windows":
            possible_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results: upscale, grayscale, and
        invert when the image is mostly dark (Tesseract strongly prefers
        dark text on a light background, while game text is usually the
        opposite).
        """
        if self.upscale > 1:
            image = image.resize(
                (image.width * self.upscale, image.height * self.upscale),
                Image.LANCZOS,
            )
        image = image.convert("L")
        if ImageStat.Stat(image).mean[0] < 128:
            image = ImageOps.invert(image)
        return image

    def extract_text(self, image: Image.Image,
                     confidence_threshold: Optional[int] = None) -> Optional[str]:
        """
        Extract text from image as a single string. Confidence filtering
        is applied via extract_text_with_boxes.
        """
        threshold = (self.confidence_threshold if confidence_threshold is None
                     else confidence_threshold)
        boxes = self.extract_text_with_boxes(image, confidence_threshold=threshold)
        if not boxes:
            return None
        return "\n".join(box["text"] for box in boxes)

    def extract_text_with_boxes(self, image: Image.Image,
                                confidence_threshold: Optional[int] = None) -> List[Dict]:
        """
        Extract text with bounding box information, merged per line.

        Tesseract returns word-level fragments; since Japanese has no
        spaces, a sentence comes back as several meaningless pieces.
        Words are merged by (block, paragraph, line) so each returned box
        is a full line suitable for translation. Coordinates are returned
        in the ORIGINAL image's pixel space (preprocessing upscale is
        compensated for).

        Returns:
            List of dicts with keys: text, x, y, width, height, confidence
        """
        threshold = (self.confidence_threshold if confidence_threshold is None
                     else confidence_threshold)
        try:
            processed = self.preprocess_image(image)
            data = pytesseract.image_to_data(
                processed,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
                config=f"--psm {self.psm}",
            )

            lines = defaultdict(list)
            for i in range(len(data["text"])):
                try:
                    conf = int(float(data["conf"][i]))
                except (TypeError, ValueError):
                    continue
                text = data["text"][i].strip()
                if conf >= threshold and text:
                    key = (data["block_num"][i], data["par_num"][i],
                           data["line_num"][i])
                    lines[key].append(i)

            scale = self.upscale
            results = []
            for idxs in lines.values():
                # Join without spaces: correct for Japanese text
                text = "".join(data["text"][i].strip() for i in idxs)
                if not text:
                    continue
                x1 = min(data["left"][i] for i in idxs)
                y1 = min(data["top"][i] for i in idxs)
                x2 = max(data["left"][i] + data["width"][i] for i in idxs)
                y2 = max(data["top"][i] + data["height"][i] for i in idxs)
                avg_conf = sum(int(float(data["conf"][i])) for i in idxs) / len(idxs)
                results.append({
                    "text": text,
                    "x": x1 // scale,
                    "y": y1 // scale,
                    "width": max(1, (x2 - x1) // scale),
                    "height": max(1, (y2 - y1) // scale),
                    "confidence": avg_conf,
                })

            # Top-to-bottom, left-to-right reading order
            results.sort(key=lambda b: (b["y"], b["x"]))
            return results
        except Exception:
            logger.exception("OCR with boxes error")
            return []

    def is_japanese_text(self, text: str) -> bool:
        """
        Check if text is plausibly Japanese: at least 30% of its
        characters in Japanese Unicode ranges and at least 2 characters
        long, which filters out single-character OCR noise.
        """
        if not text:
            return False
        stripped = text.strip()
        if len(stripped) < 2:
            return False

        japanese = 0
        for char in stripped:
            code = ord(char)
            # Hiragana: 3040-309F, Katakana: 30A0-30FF (incl. chōonpu),
            # CJK ideographs: 4E00-9FFF, iteration mark 々: 3005,
            # half-width katakana FF66-FF9F (common in retro games)
            if (0x3040 <= code <= 0x309F or
                    0x30A0 <= code <= 0x30FF or
                    0x4E00 <= code <= 0x9FFF or
                    code == 0x3005 or
                    0xFF66 <= code <= 0xFF9F):
                japanese += 1
        return japanese > 0 and (japanese / len(stripped)) >= 0.3
