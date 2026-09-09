"""Client-area capture adapter for a selected game window."""

from __future__ import annotations

from typing import Any

import numpy as np


class GameWindowCapture:
    """Capture only a valid target's client area through Pillow on Windows."""

    def capture(self, hwnd: int) -> np.ndarray | None:
        """Return an RGB client-area image, or ``None`` when capture is unavailable."""
        try:
            import win32gui
            from PIL import ImageGrab
        except ImportError as error:
            raise RuntimeError("window capture requires pywin32 and Pillow") from error
        if not win32gui.IsWindow(hwnd):
            return None
        left, top = win32gui.ClientToScreen(hwnd, (0, 0))
        _, _, right, bottom = win32gui.GetClientRect(hwnd)
        if right <= 0 or bottom <= 0:
            return None
        image = ImageGrab.grab(bbox=(left, top, left + right, top + bottom), all_screens=True)
        return np.asarray(image.convert("RGB"))
