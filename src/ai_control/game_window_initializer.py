"""Normalize a selected MU window before Gemini starts OCR-dependent work."""

from __future__ import annotations

import json
from pathlib import Path
import time

from src.logic.system_executor.mouse_controller import MouseController


CLIENT_WIDTH = 800
CLIENT_HEIGHT = 600


def prepare_game_window_for_ocr(hwnd: int, teaching_path: Path) -> None:
    """Resize one game client area to 800×600 and click its zoom-reset ROI."""
    import win32con
    import win32gui

    window_rect = win32gui.GetWindowRect(hwnd)
    client_rect = win32gui.GetClientRect(hwnd)
    client_width = client_rect[2] - client_rect[0]
    client_height = client_rect[3] - client_rect[1]
    outer_width = window_rect[2] - window_rect[0]
    outer_height = window_rect[3] - window_rect[1]

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetWindowPos(
        hwnd,
        None,
        window_rect[0],
        window_rect[1],
        CLIENT_WIDTH + (outer_width - client_width),
        CLIENT_HEIGHT + (outer_height - client_height),
        win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER,
    )
    time.sleep(0.2)

    payload = json.loads(teaching_path.read_text(encoding="utf-8-sig"))
    roi = payload["mainInfo"]["resetScreenRoom"]["roi"]
    client_x = (int(roi["x1"]) + int(roi["x2"])) // 2
    client_y = (int(roi["y1"]) + int(roi["y2"])) // 2
    MouseController(target_window_hwnd=hwnd).click_at_client(client_x, client_y)
