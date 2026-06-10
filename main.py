#!/usr/bin/env python3
"""
J2EOverlay - Japanese to English Overlay Translation Tool
Main application entry point
"""

import argparse
import logging
import sys
import os

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QDialog
from PyQt5.QtCore import QTimer, Qt, QObject, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from pynput import keyboard

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from src.pipeline import TranslationWorker
from src.overlay import TranslationOverlay, RegionSelector

logger = logging.getLogger("j2eoverlay")


class CaptureTrigger(QObject):
    """Cross-thread bridge: emitting `fire` queues a job onto the worker
    thread. Safe to emit from any thread, including pynput's listener."""
    fire = pyqtSignal(object)


class HotkeyBridge(QObject):
    """Marshals pynput hotkey callbacks (which run on the listener
    thread) onto the Qt main thread via queued signals."""
    capture = pyqtSignal()
    toggle = pyqtSignal()
    quit = pyqtSignal()


def make_tray_icon() -> QIcon:
    """Generate a simple tray icon at runtime so the tray entry is never
    invisible (QSystemTrayIcon without an icon may not render at all)."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(30, 30, 46))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 12, 12)
    painter.setPen(QColor(0, 255, 128))
    painter.setFont(QFont("Arial", 22, QFont.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "JE")
    painter.end()
    return QIcon(pixmap)


class J2EOverlayApp:
    """Main application class for J2EOverlay"""

    def __init__(self):
        # Must be set before QApplication is created
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Load configuration
        self.config = Config()

        # Create overlay window
        self.overlay = TranslationOverlay(self.config.settings)

        # Region selector state
        self.capture_region = None  # (x, y, w, h) in logical coords, or None

        # Auto-capture timer
        self.auto_capture_timer = None
        self.auto_capture_enabled = False

        # --- Background pipeline (all heavy work off the UI thread) ---
        self._busy = False
        dpr = self.app.primaryScreen().devicePixelRatio()
        self.worker_thread = QThread()
        self.worker = TranslationWorker(self.config, device_pixel_ratio=dpr)
        self.worker.moveToThread(self.worker_thread)

        self.trigger = CaptureTrigger()
        self.trigger.fire.connect(self.worker.process)
        self.worker.results_ready.connect(self._on_results)
        self.worker.no_change.connect(self._on_no_change)
        self.worker.error.connect(self._on_error)
        self.worker.initialized.connect(self._on_worker_initialized)
        # Direct connection: runs on the worker thread as it finishes,
        # releasing the mss instance on the thread that owns it
        self.worker_thread.finished.connect(
            self.worker.shutdown, Qt.DirectConnection)
        self.worker_thread.start()

        # Setup system tray
        self._setup_system_tray()

        # Setup global hotkeys
        self._setup_hotkeys()

        logger.info("J2EOverlay started successfully!")
        logger.info("Hotkeys:")
        logger.info("  Capture & Translate: %s",
                    self.config.get('hotkey.capture', '<ctrl>+<shift>+t'))
        logger.info("  Toggle Overlay: %s",
                    self.config.get('hotkey.toggle', '<ctrl>+<shift>+o'))
        logger.info("  Quit: %s",
                    self.config.get('hotkey.quit', '<ctrl>+<shift>+q'))
        logger.info("Translation model loads in the background on first capture.")

    # ------------------------------------------------------------------
    # System tray
    # ------------------------------------------------------------------

    def _setup_system_tray(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(make_tray_icon(), self.app)

        tray_menu = QMenu()

        select_region_action = QAction("Select Region", self.app)
        select_region_action.triggered.connect(self.select_region)
        tray_menu.addAction(select_region_action)

        clear_region_action = QAction("Clear Region", self.app)
        clear_region_action.triggered.connect(self.clear_region)
        tray_menu.addAction(clear_region_action)

        tray_menu.addSeparator()

        capture_action = QAction("Capture && Translate", self.app)
        capture_action.triggered.connect(self.capture_and_translate)
        tray_menu.addAction(capture_action)

        toggle_action = QAction("Toggle Overlay", self.app)
        toggle_action.triggered.connect(self.toggle_overlay)
        tray_menu.addAction(toggle_action)

        tray_menu.addSeparator()

        self.auto_capture_action = QAction("Enable Auto-Capture", self.app)
        self.auto_capture_action.setCheckable(True)
        self.auto_capture_action.triggered.connect(self.toggle_auto_capture)
        tray_menu.addAction(self.auto_capture_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("J2EOverlay - Japanese to English Translator")
        self.tray_icon.show()

    # ------------------------------------------------------------------
    # Hotkeys
    # ------------------------------------------------------------------

    def _setup_hotkeys(self):
        """Setup global keyboard shortcuts using pynput GlobalHotKeys.

        pynput callbacks run on the listener thread; they only emit Qt
        signals here, which Qt queues onto the main thread.
        """
        self.hotkey_bridge = HotkeyBridge()
        self.hotkey_bridge.capture.connect(self.capture_and_translate)
        self.hotkey_bridge.toggle.connect(self.toggle_overlay)
        self.hotkey_bridge.quit.connect(self.quit_app)

        hotkey_map = {
            self.config.get('hotkey.capture', '<ctrl>+<shift>+t'):
                self.hotkey_bridge.capture.emit,
            self.config.get('hotkey.toggle', '<ctrl>+<shift>+o'):
                self.hotkey_bridge.toggle.emit,
            self.config.get('hotkey.quit', '<ctrl>+<shift>+q'):
                self.hotkey_bridge.quit.emit,
        }

        try:
            self.keyboard_listener = keyboard.GlobalHotKeys(hotkey_map)
            self.keyboard_listener.start()
        except Exception:
            logger.exception(
                "Failed to register global hotkeys (check config.json "
                "hotkey format, e.g. '<ctrl>+<shift>+t'). "
                "The tray menu still works.")
            self.keyboard_listener = None

    # ------------------------------------------------------------------
    # Region selection
    # ------------------------------------------------------------------

    def select_region(self):
        """Open region selector to choose capture area"""
        # Pause auto-capture while the selector covers the screen, so the
        # pipeline never OCRs the dimmed selection overlay itself
        timer_was_active = (self.auto_capture_timer is not None
                            and self.auto_capture_timer.isActive())
        if timer_was_active:
            self.auto_capture_timer.stop()
        try:
            selector = RegionSelector()
            result = selector.exec_()
        finally:
            if timer_was_active and self.auto_capture_timer is not None:
                self.auto_capture_timer.start()

        region = selector.get_selected_region()
        if result == QDialog.Accepted and region:
            self.capture_region = region
            self.worker.reset_frame_cache()
            x, y, w, h = region
            logger.info("Region selected: x=%d, y=%d, width=%d, height=%d",
                        x, y, w, h)
            self.tray_icon.showMessage(
                "Region Selected",
                f"Capture region set to {w}x{h} at ({x}, {y})",
                QSystemTrayIcon.Information,
                2000
            )

    def clear_region(self):
        """Clear the selected capture region"""
        self.capture_region = None
        self.worker.reset_frame_cache()
        logger.info("Capture region cleared")
        self.tray_icon.showMessage(
            "Region Cleared",
            "Capture region has been cleared",
            QSystemTrayIcon.Information,
            2000
        )

    # ------------------------------------------------------------------
    # Capture / translate
    # ------------------------------------------------------------------

    def capture_and_translate(self):
        """Queue one capture -> OCR -> translate cycle on the worker.

        The busy guard drops requests while a job is in flight, so
        auto-capture ticks and hotkey spam can never pile up stale jobs.
        """
        if self._busy:
            return
        self._busy = True
        self.trigger.fire.emit(self.capture_region)

    def _on_results(self, results):
        """Render translated boxes (runs on the main thread)."""
        self.overlay.set_translations(results)
        if results and not self.overlay.isVisible():
            self.overlay.show()
        if not results:
            logger.debug("No Japanese text detected")
        self._busy = False

    def _on_no_change(self):
        """Frame unchanged: keep the existing overlay (no flicker)."""
        self._busy = False

    def _on_error(self, msg):
        logger.error("Pipeline error: %s", msg)
        self._busy = False

    def _on_worker_initialized(self, device):
        logger.info("Pipeline initialized (translation device: %s)", device)
        self.tray_icon.showMessage(
            "J2EOverlay Ready",
            f"Translation model loaded ({device.upper()})",
            QSystemTrayIcon.Information,
            2000
        )

    # ------------------------------------------------------------------
    # Toggles
    # ------------------------------------------------------------------

    def toggle_overlay(self):
        """Toggle overlay visibility"""
        if self.overlay.isVisible():
            self.overlay.hide()
            logger.info("Overlay hidden")
        else:
            self.overlay.show()
            logger.info("Overlay shown")

    def toggle_auto_capture(self):
        """Toggle automatic capture mode"""
        self.auto_capture_enabled = not self.auto_capture_enabled

        if self.auto_capture_enabled:
            interval = self.config.get('capture.scan_interval', 1000)
            self.auto_capture_timer = QTimer()
            self.auto_capture_timer.timeout.connect(self.capture_and_translate)
            self.auto_capture_timer.start(interval)
            self.auto_capture_action.setText("Disable Auto-Capture")
            logger.info("Auto-capture enabled (interval: %dms)", interval)
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
            self.auto_capture_action.setText("Enable Auto-Capture")
            logger.info("Auto-capture disabled")
            self.tray_icon.showMessage(
                "Auto-Capture Disabled",
                "Manual capture mode",
                QSystemTrayIcon.Information,
                2000
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def quit_app(self):
        """Quit the application"""
        logger.info("Quitting J2EOverlay...")
        if self.auto_capture_timer:
            self.auto_capture_timer.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.worker_thread.quit()
        # The first capture can hold the worker for a long time loading
        # the model; give it a generous window, then terminate rather
        # than destroy a running QThread (which can crash on exit)
        if not self.worker_thread.wait(15000):
            logger.warning("Worker thread did not stop in time; terminating")
            self.worker_thread.terminate()
            self.worker_thread.wait(2000)
        self.overlay.close()
        self.tray_icon.hide()
        self.app.quit()

    def run(self):
        """Run the application"""
        return self.app.exec_()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="J2EOverlay")
    parser.add_argument("--debug", action="store_true",
                        help="Enable verbose debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        app = J2EOverlayApp()
        sys.exit(app.run())
    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
