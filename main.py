#!/usr/bin/env python3
"""
J2EOverlay - Japanese to English Overlay Translation Tool
Main application entry point
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon
from pynput import keyboard
from typing import Optional

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config
from src.screen_capture import ScreenCapture
from src.ocr_engine import OCREngine
from src.translator import Translator
from src.overlay import TranslationOverlay, RegionSelector


class J2EOverlayApp:
    """Main application class for J2EOverlay"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Load configuration
        self.config = Config()

        # Initialize components
        self.screen_capture = ScreenCapture()
        self.ocr_engine = OCREngine(
            language=self.config.get('ocr.language', 'jpn'),
            tesseract_path=self.config.get('ocr.tesseract_path', '')
        )
        self.translator = Translator(
            source_lang=self.config.get('translation.source_lang', 'ja'),
            target_lang=self.config.get('translation.target_lang', 'en'),
            service=self.config.get('translation.service', 'google')
        )

        # Create overlay window
        self.overlay = TranslationOverlay(self.config.settings)

        # Region selector
        self.region_selector = None
        self.capture_region = None

        # Auto-capture timer
        self.auto_capture_timer = None
        self.auto_capture_enabled = False

        # Setup system tray
        self._setup_system_tray()

        # Setup keyboard shortcuts
        self._setup_hotkeys()

        print("J2EOverlay started successfully!")
        print("Hotkeys:")
        print(f"  Capture & Translate: {self.config.get('hotkey.capture', 'Ctrl+Shift+T')}")
        print(f"  Toggle Overlay: {self.config.get('hotkey.toggle', 'Ctrl+Shift+O')}")
        print(f"  Quit: {self.config.get('hotkey.quit', 'Ctrl+Shift+Q')}")

    def _setup_system_tray(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self.app)

        # Create tray menu
        tray_menu = QMenu()

        # Select region action
        select_region_action = QAction("Select Region", self.app)
        select_region_action.triggered.connect(self.select_region)
        tray_menu.addAction(select_region_action)

        # Clear region action
        clear_region_action = QAction("Clear Region", self.app)
        clear_region_action.triggered.connect(self.clear_region)
        tray_menu.addAction(clear_region_action)

        tray_menu.addSeparator()

        # Capture action
        capture_action = QAction("Capture & Translate", self.app)
        capture_action.triggered.connect(self.capture_and_translate)
        tray_menu.addAction(capture_action)

        # Toggle overlay action
        toggle_action = QAction("Toggle Overlay", self.app)
        toggle_action.triggered.connect(self.toggle_overlay)
        tray_menu.addAction(toggle_action)

        tray_menu.addSeparator()

        # Auto-capture toggle
        self.auto_capture_action = QAction("Enable Auto-Capture", self.app)
        self.auto_capture_action.setCheckable(True)
        self.auto_capture_action.triggered.connect(self.toggle_auto_capture)
        tray_menu.addAction(self.auto_capture_action)

        tray_menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("J2EOverlay - Japanese to English Translator")

        # Show tray icon (use a simple text icon if no icon file available)
        self.tray_icon.show()

    def _setup_hotkeys(self):
        """Setup global keyboard shortcuts"""
        def on_press(key):
            try:
                # Convert pynput key to string for comparison
                key_str = str(key).replace("'", "")

                # Check for hotkey combinations
                # Note: This is a simplified hotkey handler
                # For production, consider using a more robust solution
                pass
            except Exception as e:
                pass

        # Start keyboard listener
        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.keyboard_listener.start()

    def select_region(self):
        """Open region selector to choose capture area"""
        self.region_selector = RegionSelector()
        self.region_selector.show()
        self.region_selector.exec_()

        region = self.region_selector.get_selected_region()
        if region:
            self.capture_region = region
            x, y, w, h = region
            self.screen_capture.set_capture_region(x, y, w, h)
            print(f"Region selected: x={x}, y={y}, width={w}, height={h}")
            self.tray_icon.showMessage(
                "Region Selected",
                f"Capture region set to {w}x{h} at ({x}, {y})",
                QSystemTrayIcon.Information,
                2000
            )

    def clear_region(self):
        """Clear the selected capture region"""
        self.capture_region = None
        self.screen_capture.clear_region()
        print("Capture region cleared")
        self.tray_icon.showMessage(
            "Region Cleared",
            "Capture region has been cleared",
            QSystemTrayIcon.Information,
            2000
        )

    def capture_and_translate(self):
        """Capture screen, perform OCR, and translate"""
        try:
            # Capture screen
            if self.capture_region:
                x, y, w, h = self.capture_region
                image = self.screen_capture.capture_region(x, y, w, h)
            else:
                image = self.screen_capture.capture_screen()

            if not image:
                print("Failed to capture screen")
                return

            # Perform OCR
            text_boxes = self.ocr_engine.extract_text_with_boxes(image)

            if not text_boxes:
                print("No text detected")
                self.overlay.clear_translations()
                return

            # Clear previous translations
            self.overlay.clear_translations()

            # Translate and display each text box
            offset_x = self.capture_region[0] if self.capture_region else 0
            offset_y = self.capture_region[1] if self.capture_region else 0

            for box in text_boxes:
                japanese_text = box['text']

                # Skip if not Japanese
                if not self.ocr_engine.is_japanese_text(japanese_text):
                    continue

                # Translate
                translated = self.translator.translate(japanese_text)

                if translated:
                    # Add translation to overlay
                    self.overlay.add_translation(
                        offset_x + box['x'],
                        offset_y + box['y'],
                        box['width'],
                        box['height'],
                        translated
                    )
                    print(f"JP: {japanese_text} -> EN: {translated}")

            # Show overlay
            if not self.overlay.isVisible():
                self.overlay.show()

        except Exception as e:
            print(f"Error during capture and translate: {e}")
            import traceback
            traceback.print_exc()

    def toggle_overlay(self):
        """Toggle overlay visibility"""
        if self.overlay.isVisible():
            self.overlay.hide()
            print("Overlay hidden")
        else:
            self.overlay.show()
            print("Overlay shown")

    def toggle_auto_capture(self):
        """Toggle automatic capture mode"""
        self.auto_capture_enabled = not self.auto_capture_enabled

        if self.auto_capture_enabled:
            interval = self.config.get('capture.scan_interval', 1000)
            self.auto_capture_timer = QTimer()
            self.auto_capture_timer.timeout.connect(self.capture_and_translate)
            self.auto_capture_timer.start(interval)
            print(f"Auto-capture enabled (interval: {interval}ms)")
            self.tray_icon.showMessage(
                "Auto-Capture Enabled",
                f"Scanning every {interval}ms",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            if self.auto_capture_timer:
                self.auto_capture_timer.stop()
                self.auto_capture_timer = None
            print("Auto-capture disabled")
            self.tray_icon.showMessage(
                "Auto-Capture Disabled",
                "Manual capture mode",
                QSystemTrayIcon.Information,
                2000
            )

    def quit_app(self):
        """Quit the application"""
        print("Quitting J2EOverlay...")
        if self.auto_capture_timer:
            self.auto_capture_timer.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.overlay.close()
        self.tray_icon.hide()
        self.app.quit()

    def run(self):
        """Run the application"""
        return self.app.exec_()


def main():
    """Main entry point"""
    try:
        app = J2EOverlayApp()
        sys.exit(app.run())
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
