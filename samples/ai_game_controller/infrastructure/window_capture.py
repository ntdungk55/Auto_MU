"""Reuse the application's HWND-aware game-window capture implementation."""

from __future__ import annotations

import numpy as np

from src.logic.system_executor.window_capture import WindowCapture


class GameWindowCapture:
    """Capture one selected client area through the app's PrintWindow adapter."""

    def __init__(self) -> None:
        self._captures: dict[int, WindowCapture] = {}

    def capture(self, hwnd: int) -> np.ndarray | None:
        """Return a BGR client-area image, or ``None`` when capture is unavailable."""
        try:
            import win32gui
        except ImportError as error:
            raise RuntimeError("window capture requires pywin32") from error
        if not win32gui.IsWindow(hwnd):
            return None
        capture = self._captures.get(int(hwnd))
        if capture is None:
            capture = WindowCapture(target_window_hwnd=int(hwnd), debug_output=False)
            self._captures[int(hwnd)] = capture
        else:
            capture.set_target_window(int(hwnd))
        return capture.capture()
