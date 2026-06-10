"""Translation module for Japanese to English translation - Offline support"""

import logging
import os
from typing import Optional, List

import torch

logger = logging.getLogger(__name__)

PRIMARY_MODEL = "staka/fugumt-ja-en"
FALLBACK_MODEL = "Helsinki-NLP/opus-mt-ja-en"


class Translator:
    """Handles translation operations with offline support"""

    def __init__(self, source_lang: str = "ja", target_lang: str = "en",
                 model_path: Optional[str] = None, fp16: bool = False):
        """
        Args:
            model_path: Custom local model directory (overrides defaults)
            fp16: Run the model in half precision on CUDA. Roughly
                doubles GPU throughput, but Marian-style models can
                occasionally emit NaNs in fp16 (blank translations), so
                this is opt-in.
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.model_path = model_path
        self.fp16 = fp16
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.translator = None
        self.tokenizer = None
        self.model_name = None
        self._initialize_translator()

    def _initialize_translator(self):
        """Initialize the translation model.

        Loading order, all offline-first so the app never silently hits
        the network at startup:
          1. Custom local model path, if provided
          2. PRIMARY_MODEL from local cache
          3. FALLBACK_MODEL from local cache
          4. PRIMARY_MODEL from network (last resort, with a clear message)
        """
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError:
            logger.error("transformers library not installed! "
                         "Install with: pip install transformers torch sentencepiece")
            return

        candidates = []
        if self.model_path and os.path.exists(self.model_path):
            candidates.append((self.model_path, True))
        candidates.append((PRIMARY_MODEL, True))
        candidates.append((FALLBACK_MODEL, True))
        candidates.append((PRIMARY_MODEL, False))  # network, last resort

        for model_name, local_only in candidates:
            try:
                if not local_only:
                    logger.warning(
                        "No translation model found in the local cache. "
                        "Attempting a one-time download of %s. "
                        "(Tip: run 'python download_models.py' beforehand.)",
                        model_name)
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name, local_files_only=local_only)
                self.translator = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name, local_files_only=local_only)
                self.model_name = model_name
                break
            except Exception as e:
                logger.info("Could not load %s (local_only=%s): %s",
                            model_name, local_only, e)
                self.tokenizer = None
                self.translator = None

        if self.translator is None:
            logger.error("Failed to load any translation model. "
                         "Run 'python download_models.py' first.")
            return

        self.translator.to(self.device)
        if self.device == "cuda" and self.fp16:
            self.translator.half()
        self.translator.eval()
        logger.info("Translation model '%s' loaded on %s",
                    self.model_name, self.device)

        # Warm-up: the first inference pays one-time lazy-init costs
        # (CUDA kernels etc.); do it now instead of on the user's first capture
        try:
            self.translate_batch(["テスト"])
            logger.debug("Translator warm-up complete")
        except Exception:
            logger.exception("Translator warm-up failed")

    def is_initialized(self) -> bool:
        return self.translator is not None and self.tokenizer is not None

    def translate(self, text: str) -> Optional[str]:
        """
        Translate a single text from Japanese to English (offline).
        Routed through translate_batch so there is one code path.
        """
        if not text or not text.strip():
            return None
        return self.translate_batch([text])[0]

    def translate_batch(self, texts: List[str]) -> List[Optional[str]]:
        """
        Translate multiple texts in a single forward pass.

        Args:
            texts: List of texts to translate

        Returns:
            List of translated texts (None for entries that failed or
            were empty), index-aligned with the input.
        """
        if not texts:
            return []

        if not self.is_initialized():
            logger.error("Translator not initialized")
            return [None] * len(texts)

        try:
            valid = [(i, t.strip()) for i, t in enumerate(texts) if t and t.strip()]
            if not valid:
                return [None] * len(texts)
            indices, clean_texts = zip(*valid)

            inputs = self.tokenizer(
                list(clean_texts),
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.inference_mode():
                outputs = self.translator.generate(
                    **inputs,
                    max_length=512,
                    num_beams=4,
                    early_stopping=True,
                    # Suppresses the classic Marian failure mode of
                    # repeating a phrase endlessly on game text
                    no_repeat_ngram_size=3,
                )

            translations = self.tokenizer.batch_decode(
                outputs, skip_special_tokens=True)

            results: List[Optional[str]] = [None] * len(texts)
            for idx, translation in zip(indices, translations):
                results[idx] = translation.strip()
            return results

        except Exception:
            logger.exception("Batch translation error")
            return [None] * len(texts)

    def is_valid_translation(self, original: str, translated: str) -> bool:
        """
        Check if a translation is usable: non-empty and not an echo of
        the input (a known failure mode of Marian-style models).
        """
        if not translated or not translated.strip():
            return False
        return original.strip() != translated.strip()

    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        if not self.translator:
            return {"status": "not_loaded"}
        return {
            "status": "loaded",
            "device": self.device,
            "fp16": self.fp16,
            "model": self.model_name,
            "model_path": self.model_path if self.model_path else "default",
            "cuda_available": torch.cuda.is_available(),
        }
