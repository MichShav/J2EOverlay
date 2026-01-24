"""Configuration management for J2EOverlay"""

import json
import os
from typing import Dict, Any


class Config:
    """Configuration manager for application settings"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.settings = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._get_default_config()
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "hotkey": {
                "capture": "<ctrl>+<shift>+t",
                "toggle": "<ctrl>+<shift>+o",
                "quit": "<ctrl>+<shift>+q"
            },
            "ocr": {
                "language": "jpn",
                "tesseract_path": "",
                "confidence_threshold": 60
            },
            "translation": {
                "source_lang": "ja",
                "target_lang": "en",
                "service": "google"
            },
            "overlay": {
                "font_size": 14,
                "font_family": "Arial",
                "text_color": "#FFFFFF",
                "background_color": "#000000",
                "background_opacity": 0.7,
                "border_color": "#00FF00",
                "border_width": 2,
                "padding": 10
            },
            "capture": {
                "mode": "region",
                "monitor": 0,
                "auto_detect": True,
                "scan_interval": 1000
            }
        }

    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'ocr.language')"""
        keys = key_path.split('.')
        value = self.settings
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        config = self.settings
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
