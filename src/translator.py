"""Translation module for Japanese to English translation - Offline support"""

import os
import torch
from typing import Optional, List
from pathlib import Path


class Translator:
    """Handles translation operations with offline support"""

    def __init__(self, source_lang: str = "ja", target_lang: str = "en",
                 service: str = "sugoi", model_path: Optional[str] = None):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.service = service
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.translator = None
        self.tokenizer = None
        self._initialize_translator()

    def _initialize_translator(self):
        """Initialize the translation service"""
        if self.service == "sugoi":
            self._initialize_sugoi()
        elif self.service == "offline":
            self._initialize_offline_model()
        else:
            # Fallback to offline model
            self._initialize_offline_model()

    def _initialize_sugoi(self):
        """Initialize Sugoi-compatible offline translation"""
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            # Use Sugoi-compatible model or best available Japanese game translation model
            # Priority: 1. Custom Sugoi model if provided
            #          2. staka/fugumt-ja-en (game-optimized)
            #          3. Helsinki-NLP/opus-mt-ja-en (fallback)

            if self.model_path and os.path.exists(self.model_path):
                model_name = self.model_path
                print(f"Loading custom Sugoi model from: {model_name}")
            else:
                # Try game-optimized model first
                model_name = "staka/fugumt-ja-en"
                print(f"Loading game-optimized translation model: {model_name}")

            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.translator = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            except Exception as e:
                # Fallback to reliable Helsinki model
                print(f"Failed to load {model_name}, falling back to Helsinki model: {e}")
                model_name = "Helsinki-NLP/opus-mt-ja-en"
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.translator = AutoModelForSeq2SeqLM.from_pretrained(model_name)

            self.translator.to(self.device)
            self.translator.eval()  # Set to evaluation mode for faster inference

            print(f"Translation model loaded successfully on {self.device}")

        except ImportError:
            print("ERROR: transformers library not installed!")
            print("Install with: pip install transformers torch sentencepiece")
            self.translator = None
        except Exception as e:
            print(f"Error initializing Sugoi translator: {e}")
            self.translator = None

    def _initialize_offline_model(self):
        """Initialize generic offline translation model"""
        self._initialize_sugoi()  # Use same implementation

    def translate(self, text: str) -> Optional[str]:
        """
        Translate text from Japanese to English (offline)

        Args:
            text: Text to translate

        Returns:
            Translated text or None if translation fails
        """
        if not text or not text.strip():
            return None

        if not self.translator or not self.tokenizer:
            print("Translator not initialized")
            return None

        try:
            # Prepare input
            inputs = self.tokenizer(text.strip(), return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate translation
            with torch.no_grad():
                outputs = self.translator.generate(
                    **inputs,
                    max_length=512,
                    num_beams=4,  # Beam search for better quality
                    early_stopping=True
                )

            # Decode output
            translated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translated.strip()

        except Exception as e:
            print(f"Translation error: {e}")
            return None

    def translate_batch(self, texts: List[str]) -> List[Optional[str]]:
        """
        Translate multiple texts efficiently

        Args:
            texts: List of texts to translate

        Returns:
            List of translated texts
        """
        if not texts:
            return []

        if not self.translator or not self.tokenizer:
            print("Translator not initialized")
            return [None] * len(texts)

        try:
            # Filter out empty texts
            valid_texts = [(i, text.strip()) for i, text in enumerate(texts) if text and text.strip()]

            if not valid_texts:
                return [None] * len(texts)

            indices, clean_texts = zip(*valid_texts)

            # Batch tokenization
            inputs = self.tokenizer(
                list(clean_texts),
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate translations
            with torch.no_grad():
                outputs = self.translator.generate(
                    **inputs,
                    max_length=512,
                    num_beams=4,
                    early_stopping=True
                )

            # Decode outputs
            translations = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)

            # Map back to original indices
            results = [None] * len(texts)
            for idx, translation in zip(indices, translations):
                results[idx] = translation.strip()

            return results

        except Exception as e:
            print(f"Batch translation error: {e}")
            return [None] * len(texts)

    def is_valid_translation(self, original: str, translated: str) -> bool:
        """
        Check if translation is valid (not same as original)

        Args:
            original: Original text
            translated: Translated text

        Returns:
            True if translation is valid
        """
        if not translated:
            return False
        return original.strip() != translated.strip()

    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        if not self.translator:
            return {"status": "not_loaded"}

        return {
            "status": "loaded",
            "device": self.device,
            "service": self.service,
            "model_path": self.model_path if self.model_path else "default",
            "cuda_available": torch.cuda.is_available()
        }
