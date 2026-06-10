"""Screen capture functionality for J2EOverlay"""

import logging
from typing import Tuple, Optional

import mss
from PIL import Image

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Handles screen capture operations across platforms.

    Note: mss instances have thread affinity. Create this object on the
    same thread that will call its capture methods (the pipeline worker
    thread does this).
    """

    def __init__(self):
        self.sct = mss.mss()
        self.monitors = self.sct.monitors
        # NOTE: named _region (not capture_region) so the instance
        # attribute does not shadow the capture_region() method.
        self._region = None

    def get_monitors(self) -> list:
        """Get list of available monitors"""
        return self.monitors

    def set_capture_region(self, x: int, y: int, width: int, height: int) -> None:
        """Set a default region used by capture_screen()"""
        self._region = {
            "left": x,
            "top": y,
            "width": width,
            "height": height,
        }

    def capture_screen(self, monitor: int = 1) -> Optional[Image.Image]:
        """
        Capture a screenshot from the stored region if set, otherwise
        from the specified monitor.

        Args:
            monitor: Monitor index (0 for all monitors, 1+ for a specific one)

        Returns:
            PIL Image object or None if capture fails
        """
        try:
            if self._region:
                screenshot = self.sct.grab(self._region)
            else:
                screenshot = self.sct.grab(self.monitors[monitor])
            return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        except Exception:
            logger.exception("Error capturing screen")
            return None

    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[Image.Image]:
        """
        Capture a specific region of the screen (physical pixels).

        Args:
            x, y: Top-left coordinates
            width, height: Dimensions of the region

        Returns:
            PIL Image object or None if capture fails
        """
        try:
            region = {"left": x, "top": y, "width": width, "height": height}
            screenshot = self.sct.grab(region)
            return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        except Exception:
            logger.exception("Error capturing region")
            return None

    def get_region_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get current stored capture region bounds"""
        if self._region:
            return (
                self._region["left"],
                self._region["top"],
                self._region["width"],
                self._region["height"],
            )
        return None

    def clear_region(self) -> None:
        """Clear the stored capture region"""
        self._region = None

    def close(self) -> None:
        """Release the mss instance"""
        try:
            self.sct.close()
        except Exception:
            pass
