"""Translation module for Japanese to English translation"""

from deep_translator import GoogleTranslator
from typing import Optional, List


class Translator:
    """Handles translation operations"""

    def __init__(self, source_lang: str = "ja", target_lang: str = "en", service: str = "google"):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.service = service
        self.translator = self._initialize_translator()

    def _initialize_translator(self):
        """Initialize the translation service"""
        if self.service == "google":
            return GoogleTranslator(source=self.source_lang, target=self.target_lang)
        else:
            # Default to Google Translator
            return GoogleTranslator(source=self.source_lang, target=self.target_lang)

    def translate(self, text: str) -> Optional[str]:
        """
        Translate text from source to target language

        Args:
            text: Text to translate

        Returns:
            Translated text or None if translation fails
        """
        if not text or not text.strip():
            return None

        try:
            translated = self.translator.translate(text.strip())
            return translated
        except Exception as e:
            print(f"Translation error: {e}")
            return None

    def translate_batch(self, texts: List[str]) -> List[Optional[str]]:
        """
        Translate multiple texts

        Args:
            texts: List of texts to translate

        Returns:
            List of translated texts
        """
        results = []
        for text in texts:
            translated = self.translate(text)
            results.append(translated)
        return results

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
