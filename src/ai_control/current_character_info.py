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
    match = re.fullmatch(r"([A-Za-z][A-Za-z '\-]{1,40}?)(?:\s+\d{1,3})?", text)
    if match is None:
        return None
    return match.group(1).strip()


def _normalize_position(raw_text: str) -> dict[str, int] | None:
    """Accept only the taught `xxx,yyy` HUD coordinate format."""
    text = " ".join(str(raw_text or "").split()).strip()
    match = re.fullmatch(r"\(?\s*(\d{1,3})\s*[,.;]\s*(\d{1,3})\s*\)?", text)
    if match is None:
        return None
    return {"x": int(match.group(1)), "y": int(match.group(2))}


def _read_taught_hud_text(
    image: Any, definition: dict[str, Any], normalizer: Any,
) -> tuple[Any, dict[str, Any]]:
    """OCR one configured HUD ROI with WinRT then EasyOCR fallback."""
    roi = {axis: int(value) for axis, value in dict(definition["roi"]).items()}
    if not (0 <= roi["x1"] < roi["x2"] <= image.shape[1] and 0 <= roi["y1"] < roi["y2"] <= image.shape[0]):
        raise ValueError(f"Current HUD ROI lies outside the captured image: {roi}")
    crop = image[roi["y1"]:roi["y2"], roi["x1"]:roi["x2"]]
    ocr_image = cv2.copyMakeBorder(crop, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    ocr_image = cv2.resize(ocr_image, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    winrt_error = None
    try:
        winrt_raw = " ".join(WinRTOCREngine().recognize(ocr_image).split())
    except Exception as error:
        winrt_raw = ""
        winrt_error = str(error)
    value = normalizer(winrt_raw)
    attempts: dict[str, str] = {"winrt": winrt_raw}
    if winrt_error:
        attempts["winrt_error"] = winrt_error
    method, confidence = "winrt", None
    if value is None:
        reader = EasyOCREngine()._get_reader()
        items = [] if reader is None else reader.readtext(ocr_image, detail=1, paragraph=False)
        accepted = [
            item for item in items
            if isinstance(item, (list, tuple)) and len(item) >= 3 and float(item[2]) >= 0.3
        ]
        easyocr_raw = " ".join(str(item[1]).strip() for item in accepted).strip()
        attempts["easyocr"] = easyocr_raw
        value = normalizer(easyocr_raw)
        method = "easyocr"
        confidence = min((float(item[2]) for item in accepted), default=None)
    return value, {"value": value, "raw_text": winrt_raw if method == "winrt" else attempts["easyocr"],
                   "method": method, "confidence": confidence, "roi": roi, "attempts": attempts}


def get_current_character_map(target: dict[str, Any]) -> dict[str, Any]:
    """Read the selected character's map and coordinate from taught HUD ROIs."""
    import win32gui

    result: dict[str, Any] = {
        "success": False, "target": dict(target), "map": None,
        "position": None, "coordinates": None,
    }
    stage = "validate_selected_window"
    try:
        hwnd = int(target["hwnd"])
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            raise RuntimeError("Selected game window is no longer visible")
        stage = "load_map_teaching"
        main_info = json.loads(TEACHING_PATH.read_text(encoding="utf-8-sig"))["mainInfo"]
        stage = "capture_game_window"
        image = GameWindowCapture().capture(hwnd)
        if image is None:
            raise RuntimeError("Could not capture the selected game window")
        stage = "ocr_current_map"
        value, result["ocr"] = _read_taught_hud_text(image, main_info["map"], _normalize_map)
        if value is None:
            raise RuntimeError("Could not read the current character map")
        stage = "ocr_current_position"
        position, result["position_ocr"] = _read_taught_hud_text(image, main_info["position"], _normalize_position)
        if position is None:
            raise RuntimeError("Could not read the current character coordinates")
        result.update(success=True, map=value, position=position,
                      coordinates=f"{position['x']},{position['y']}",
                      is_varka=value.casefold() == "varka")
    except Exception as error:
        result.update(success=False, error=str(error), debug={"stage": stage, "exception_type": type(error).__name__, "traceback": traceback.format_exc(limit=5)})
    return result
