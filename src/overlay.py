"""Transparent overlay window for displaying translations"""

from typing import Optional, Tuple

from PyQt5.QtWidgets import QWidget, QDialog, QApplication
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPalette, QColor, QFont, QPainter, QPen


class TranslationOverlay(QWidget):
    """Transparent overlay window that displays translated text"""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.translation_boxes = []  # List of (rect, text) tuples
        self._setup_window()

    def _setup_window(self):
        """Setup the overlay window properties"""
        # Window flags for transparent, always-on-top, frameless window
        # that works with fullscreen applications
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput  # Click-through
        )

        # Set window to cover entire screen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # Make window transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Don't show in taskbar
        self.setAttribute(Qt.WA_X11DoNotAcceptFocus, True)

        # Set up font and colors. Named overlay_font (not font) so it
        # does not shadow QWidget.font().
        self.overlay_font = QFont(
            self.config.get('overlay', {}).get('font_family', 'Arial'),
            self.config.get('overlay', {}).get('font_size', 14)
        )

        self.text_color = QColor(
            self.config.get('overlay', {}).get('text_color', '#FFFFFF')
        )
        self.bg_color = QColor(
            self.config.get('overlay', {}).get('background_color', '#000000')
        )
        self.border_color = QColor(
            self.config.get('overlay', {}).get('border_color', '#00FF00')
        )

        # Set background opacity
        opacity = self.config.get('overlay', {}).get('background_opacity', 0.7)
        self.bg_color.setAlphaF(opacity)

        self.border_width = self.config.get('overlay', {}).get('border_width', 2)
        self.padding = self.config.get('overlay', {}).get('padding', 10)

    def set_translations(self, boxes):
        """Replace all translation boxes in one repaint.

        Args:
            boxes: iterable of (x, y, width, height, text) tuples
        """
        self.translation_boxes = [
            (QRect(x, y, w, h), text) for x, y, w, h, text in boxes
        ]
        self.update()

    def clear_translations(self):
        """Clear all translation boxes"""
        self.translation_boxes.clear()
        self.update()

    def paintEvent(self, event):
        """Custom paint event to draw translation boxes"""
        if not self.translation_boxes:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self.overlay_font)

        for rect, text in self.translation_boxes:
            # Draw background
            painter.fillRect(rect, self.bg_color)

            # Draw border
            pen = QPen(self.border_color, self.border_width)
            painter.setPen(pen)
            painter.drawRect(rect)

            # Draw text
            painter.setPen(self.text_color)
            text_rect = rect.adjusted(
                self.padding,
                self.padding,
                -self.padding,
                -self.padding
            )
            painter.drawText(
                text_rect,
                Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                text
            )

    def update_config(self, config: dict):
        """Update overlay configuration"""
        was_visible = self.isVisible()
        self.config = config
        self._setup_window()
        # setWindowFlags() hides the window; restore visibility
        if was_visible:
            self.show()
        self.update()


class RegionSelector(QDialog):
    """Dialog for selecting a screen region to capture.

    Must be a QDialog (not a plain QWidget) so exec_() exists and blocks
    until the user finishes or cancels the selection.
    """

    def __init__(self):
        super().__init__()
        self.begin_pos = None
        self.end_pos = None
        self.is_selecting = False
        self.selected_region = None
        self._setup_window()

    def _setup_window(self):
        """Setup the region selector window"""
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )

        # Make semi-transparent
        self.setWindowOpacity(0.3)

        # Cover entire screen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # Set background color
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 128))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        """Handle mouse press to start selection"""
        if event.button() == Qt.LeftButton:
            self.begin_pos = event.pos()
            self.is_selecting = True

    def mouseMoveEvent(self, event):
        """Handle mouse move during selection"""
        if self.is_selecting:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release to finish selection"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.end_pos = event.pos()
            self.is_selecting = False

            # Calculate selected region
            if self.begin_pos and self.end_pos:
                x = min(self.begin_pos.x(), self.end_pos.x())
                y = min(self.begin_pos.y(), self.end_pos.y())
                width = abs(self.end_pos.x() - self.begin_pos.x())
                height = abs(self.end_pos.y() - self.begin_pos.y())

                if width > 10 and height > 10:  # Minimum size
                    self.selected_region = (x, y, width, height)

            if self.selected_region:
                self.accept()
            else:
                self.reject()

    def paintEvent(self, event):
        """Draw selection rectangle"""
        super().paintEvent(event)

        if self.begin_pos and self.end_pos and self.is_selecting:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw selection rectangle
            pen = QPen(QColor(0, 255, 0), 2)
            painter.setPen(pen)

            x = min(self.begin_pos.x(), self.end_pos.x())
            y = min(self.begin_pos.y(), self.end_pos.y())
            width = abs(self.end_pos.x() - self.begin_pos.x())
            height = abs(self.end_pos.y() - self.begin_pos.y())

            painter.drawRect(x, y, width, height)

    def get_selected_region(self) -> Optional[Tuple[int, int, int, int]]:
        """Get the selected region coordinates (logical screen coords)"""
        return self.selected_region

    def keyPressEvent(self, event):
        """Handle Escape key to cancel selection"""
        if event.key() == Qt.Key_Escape:
            self.selected_region = None
            self.reject()
