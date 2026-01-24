"""Screen capture functionality for J2EOverlay"""

import mss
import numpy as np
from PIL import Image
from typing import Tuple, Optional


class ScreenCapture:
    """Handles screen capture operations across platforms"""

    def __init__(self):
        self.sct = mss.mss()
        self.monitors = self.sct.monitors
        self.capture_region = None

    def get_monitors(self) -> list:
        """Get list of available monitors"""
        return self.monitors

    def set_capture_region(self, x: int, y: int, width: int, height: int) -> None:
        """Set the region to capture"""
        self.capture_region = {
            "left": x,
            "top": y,
            "width": width,
            "height": height
        }

    def capture_screen(self, monitor: int = 1) -> Optional[Image.Image]:
        """
        Capture screenshot from specified monitor

        Args:
            monitor: Monitor index (0 for all monitors, 1+ for specific monitor)

        Returns:
            PIL Image object or None if capture fails
        """
        try:
            if self.capture_region:
                screenshot = self.sct.grab(self.capture_region)
            else:
                screenshot = self.sct.grab(self.monitors[monitor])

            # Convert to PIL Image
            img = Image.frombytes(
                "RGB",
                screenshot.size,
                screenshot.rgb
            )
            return img
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None

    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[Image.Image]:
        """
        Capture a specific region of the screen

        Args:
            x, y: Top-left coordinates
            width, height: Dimensions of the region

        Returns:
            PIL Image object or None if capture fails
        """
        try:
            region = {
                "left": x,
                "top": y,
                "width": width,
                "height": height
            }
            screenshot = self.sct.grab(region)
            img = Image.frombytes(
                "RGB",
                screenshot.size,
                screenshot.rgb
            )
            return img
        except Exception as e:
            print(f"Error capturing region: {e}")
            return None

    def get_region_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get current capture region bounds"""
        if self.capture_region:
            return (
                self.capture_region["left"],
                self.capture_region["top"],
                self.capture_region["width"],
                self.capture_region["height"]
            )
        return None

    def clear_region(self) -> None:
        """Clear the capture region"""
        self.capture_region = None
