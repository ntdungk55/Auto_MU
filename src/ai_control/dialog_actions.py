"""Close an image-verified game dialog using its teaching configuration."""

from __future__ import annotations

import time
from typing import Any

import cv2

from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control.companion_switcher import _match
from src.logic.system_executor.mouse_controller import MouseController


def close_taught_dialog(hwnd: int, layout: dict[str, Any], template: Any,
                             threshold: float, timeout_seconds: float, dialog_name: str) -> dict[str, Any]:
    """Locate the current dialog, click its taught X button, and verify title disappearance."""
    import win32gui

    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        raise RuntimeError("Selected window is unavailable for dialog close verification")
    capture = GameWindowCapture()
    image = capture.capture(hwnd)
    if image is None:
        raise RuntimeError("Could not capture the dialog before closing")
    title = _match(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), template, f"{dialog_name} title")
    if title["score"] < threshold:
        return {"closed": True, "click_sent": False, "score": title["score"], "threshold": threshold}
    close = layout["buttons"]["close"]
    if "roiRelativeToTitle" in close:
        relative, offset = close["roiRelativeToTitle"], {"x": 0, "y": 0}
    else:
        relative, offset = close["roi"], layout["Anchor"]["dialogOriginOffset"]
    roi = {axis: int(relative[axis]) + int(title["bbox"][axis[0] + "1"]) + int(offset[axis[0]])
           for axis in ("x1", "y1", "x2", "y2")}
    if not (0 <= roi["x1"] < roi["x2"] <= image.shape[1]
            and 0 <= roi["y1"] < roi["y2"] <= image.shape[0]):
        raise ValueError(f"{dialog_name} close button lies outside the captured image: {roi}")
    x, y = (roi["x1"] + roi["x2"]) // 2, (roi["y1"] + roi["y2"]) // 2
    MouseController(target_window_hwnd=hwnd).click_at_client(x, y)
    result = {"closed": False, "click_sent": True, "button": {"x": x, "y": y},
              "roi": roi, "threshold": threshold}
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        image = capture.capture(hwnd)
        if image is not None:
            match = _match(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), template, f"{dialog_name} title")
            result["score"] = match["score"]
            if match["score"] < threshold:
                result["closed"] = True
                return result
        time.sleep(0.05)
    result["error"] = f"Could not verify {dialog_name} closed after clicking X"
    return result
