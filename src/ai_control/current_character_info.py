"""Read current-character information from the persistent game HUD."""

from __future__ import annotations

import json
import re
import traceback
from typing import Any

import cv2

from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control.companion_switcher import PROJECT_ROOT, TEACHING_PATH
from src.logic.system_executor.ocr_engine import EasyOCREngine, WinRTOCREngine


def _normalize_map(raw_text: str) -> str | None:
    text = " ".join(str(raw_text or "").split()).strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z '\-]{1,40}", text):
        return None
    return text


def get_current_character_map(target: dict[str, Any]) -> dict[str, Any]:
    """Read and normalize the selected character's map from the taught HUD ROI."""
    import win32gui

    result: dict[str, Any] = {"success": False, "target": dict(target), "map": None}
    stage = "validate_selected_window"
    try:
        hwnd = int(target["hwnd"])
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            raise RuntimeError("Selected game window is no longer visible")
        stage = "load_map_teaching"
        definition = json.loads(TEACHING_PATH.read_text(encoding="utf-8-sig"))["mainInfo"]["map"]
        roi = {axis: int(value) for axis, value in dict(definition["roi"]).items()}
        stage = "capture_game_window"
        image = GameWindowCapture().capture(hwnd)
        if image is None:
            raise RuntimeError("Could not capture the selected game window")
        if not (0 <= roi["x1"] < roi["x2"] <= image.shape[1] and 0 <= roi["y1"] < roi["y2"] <= image.shape[0]):
            raise ValueError(f"Current map ROI lies outside the captured image: {roi}")
        stage = "ocr_current_map"
        crop = image[roi["y1"]:roi["y2"], roi["x1"]:roi["x2"]]
        ocr_image = cv2.copyMakeBorder(crop, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        ocr_image = cv2.resize(ocr_image, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        winrt_error = None
        try:
            winrt_raw = " ".join(WinRTOCREngine().recognize(ocr_image).split())
        except Exception as error:
            winrt_raw = ""
            winrt_error = str(error)
        value = _normalize_map(winrt_raw)
        attempts: dict[str, str] = {"winrt": winrt_raw}
        if winrt_error:
            attempts["winrt_error"] = winrt_error
        method, confidence = "winrt", None
        if value is None:
            reader = EasyOCREngine()._get_reader()
            items = [] if reader is None else reader.readtext(ocr_image, detail=1, paragraph=True)
            easyocr_raw = " ".join(str(item[1]).strip() for item in items if float(item[2]) >= 0.3).strip()
            attempts["easyocr"] = easyocr_raw
            value = _normalize_map(easyocr_raw)
            method = "easyocr"
            confidence = min((float(item[2]) for item in items), default=None)
        result["ocr"] = {"value": value, "raw_text": winrt_raw if method == "winrt" else attempts["easyocr"], "method": method,
                         "confidence": confidence, "roi": roi, "attempts": attempts}
        if value is None:
            raise RuntimeError("Could not read the current character map")
        result.update(success=True, map=value, is_varka=value.casefold() == "varka")
    except Exception as error:
        result.update(success=False, error=str(error), debug={"stage": stage, "exception_type": type(error).__name__, "traceback": traceback.format_exc(limit=5)})
    return result
