"""Background translation pipeline for J2EOverlay.

All heavy work (screen capture, OCR, model loading, translation) runs on
a dedicated worker thread so the Qt UI never blocks. Results are sent
back to the main thread via signals.
"""

import hashlib
import logging
from collections import OrderedDict

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)

CACHE_MAX_ENTRIES = 5000


class TranslationWorker(QObject):
    """Owns the capture -> OCR -> translate pipeline on a worker thread.

    Heavy initialization (mss instance, Tesseract setup, model loading)
    happens lazily on the FIRST job, on the worker thread. This keeps app
    startup instant and respects mss thread affinity.
    """

    # [(x, y, w, h, translated_text), ...] in logical screen coordinates
    results_ready = pyqtSignal(list)
    no_change = pyqtSignal()       # frame identical to last one; overlay kept as-is
    error = pyqtSignal(str)
    initialized = pyqtSignal(str)  # emitted once with device info ("cpu"/"cuda")

    def __init__(self, config, device_pixel_ratio: float = 1.0):
        super().__init__()
        self.config = config
        # Qt geometry uses logical points; mss and OCR work in physical
        # pixels. Convert at the pipeline boundary so the overlay lines up
        # on high-DPI displays (e.g. Windows 125%/150% scaling).
        self.dpr = device_pixel_ratio or 1.0
        self.screen_capture = None
        self.ocr_engine = None
        self.translator = None
        self._last_frame_sig = None
        self._cache = OrderedDict()  # jp text -> en text

    def _ensure_initialized(self):
        if self.translator is not None:
            return
        from src.screen_capture import ScreenCapture
        from src.ocr_engine import OCREngine
        from src.translator import Translator

        self.screen_capture = ScreenCapture()
        self.ocr_engine = OCREngine(
            language=self.config.get('ocr.language', 'jpn'),
            tesseract_path=self.config.get('ocr.tesseract_path', ''),
            psm=self.config.get('ocr.psm', 6),
            confidence_threshold=self.config.get('ocr.confidence_threshold', 60),
            upscale=self.config.get('ocr.upscale', 2),
        )
        self.translator = Translator(
            source_lang=self.config.get('translation.source_lang', 'ja'),
            target_lang=self.config.get('translation.target_lang', 'en'),
            model_path=self.config.get('translation.model_path', ''),
            fp16=self.config.get('translation.fp16', False),
        )
        self.initialized.emit(self.translator.device)

    @pyqtSlot(object)
    def process(self, region):
        """Run one capture -> OCR -> translate cycle.

        Args:
            region: (x, y, w, h) in logical screen coordinates, or None
                for full-screen capture.
        """
        try:
            self._ensure_initialized()

            if not self.translator.is_initialized():
                self.error.emit(
                    "Translation model not available. "
                    "Run 'python download_models.py' first.")
                return

            if region:
                px = tuple(int(v * self.dpr) for v in region)
                image = self.screen_capture.capture_region(*px)
                ox, oy = region[0], region[1]
            else:
                image = self.screen_capture.capture_screen()
                ox, oy = 0, 0

            if image is None:
                self.error.emit("Screen capture failed")
                return

            # Skip identical frames entirely (no OCR, no overlay flicker)
            sig = self._frame_signature(image, full_screen=region is None)
            if sig == self._last_frame_sig:
                self.no_change.emit()
                return
            self._last_frame_sig = sig

            boxes = self.ocr_engine.extract_text_with_boxes(image)
            jp_boxes = [b for b in boxes
                        if self.ocr_engine.is_japanese_text(b['text'])]

            # Translate only what the cache doesn't already have,
            # de-duplicated, in a single batched forward pass
            pending = list(OrderedDict.fromkeys(
                b['text'] for b in jp_boxes if b['text'] not in self._cache))
            if pending:
                translations = self.translator.translate_batch(pending)
                for jp, en in zip(pending, translations):
                    if en and self.translator.is_valid_translation(jp, en):
                        self._cache[jp] = en
                while len(self._cache) > CACHE_MAX_ENTRIES:
                    self._cache.popitem(last=False)

            results = []
            for b in jp_boxes:
                en = self._cache.get(b['text'])
                if not en:
                    continue
                # Keep recurring text fresh so eviction is true LRU
                self._cache.move_to_end(b['text'])
                results.append((
                    int(ox + b['x'] / self.dpr),
                    int(oy + b['y'] / self.dpr),
                    max(1, int(b['width'] / self.dpr)),
                    max(1, int(b['height'] / self.dpr)),
                    en,
                ))
                logger.info("JP: %s -> EN: %s", b['text'], en)

            self.results_ready.emit(results)

        except Exception as e:
            logger.exception("Pipeline error")
            self.error.emit(str(e))

    def reset_frame_cache(self):
        """Force the next capture to be processed even if unchanged
        (e.g. after the user changes the capture region)."""
        self._last_frame_sig = None

    def _frame_signature(self, image, full_screen: bool = False) -> str:
        """Cheap signature of a frame: downscale + grayscale + hash.

        Exact matching is deliberately strict: animated scenes rarely
        match, but the translation cache absorbs the repeated text, which
        is where the real cost is. Full-screen captures use a larger
        thumbnail so a one-line dialogue change in a corner of the screen
        is not quantized away.
        """
        size = (192, 108) if full_screen else (64, 36)
        small = image.resize(size).convert('L')
        return hashlib.md5(small.tobytes()).hexdigest()

    def shutdown(self):
        """Release worker-owned resources. Connected to QThread.finished
        with a direct connection so it runs on the worker thread itself,
        respecting mss thread affinity."""
        if self.screen_capture is not None:
            self.screen_capture.close()
