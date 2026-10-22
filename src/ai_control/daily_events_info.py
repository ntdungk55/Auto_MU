"""Read the five Daily Events remaining-entry counters from title-relative teaching."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

import cv2

from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control.companion_switcher import PROJECT_ROOT, TEACHING_PATH, _load_template, _match
from src.ai_control.dialog_actions import close_taught_dialog
from src.logic.system_executor.ocr_engine import EasyOCREngine


def _read_remaining(image: Any, title: dict[str, Any], layout: dict[str, Any]) -> dict[str, Any]:
    """Read each taught row independently; missing or ambiguous numbers remain unknown."""
    settings = layout["textRecognition"]
    scale, padding = float(settings["scale"]), int(settings["padding"])
    minimum_confidence = float(settings["minimumConfidence"])
    if settings["engine"] != "easyocr" or not (1 <= scale <= 8 and 0 <= padding <= 32
                                               and 0 <= minimum_confidence <= 1):
        raise ValueError("Invalid Daily Events textRecognition settings")
    reader = EasyOCREngine()._get_reader()
    if reader is None:
        raise RuntimeError("EasyOCR is unavailable for Daily Events")
    fields: dict[str, Any] = {}
    for key in ("boss", "jewel", "bc", "devil", "ig"):
        definition = layout["textRegions"][key]
        relative = definition["roiRelativeToTitle"]
        roi = {axis: int(relative[axis]) + int(title["bbox"][axis[0] + "1"])
               for axis in ("x1", "y1", "x2", "y2")}
        field: dict[str, Any] = {"value": None, "raw_text": "", "confidence": None,
                                 "method": "easyocr", "roi": roi}
        fields[key] = field
        try:
            x1, y1, x2, y2 = (roi[axis] for axis in ("x1", "y1", "x2", "y2"))
            if not (0 <= x1 < x2 <= image.shape[1] and 0 <= y1 < y2 <= image.shape[0]):
                raise ValueError("The taught value region lies outside the captured window")
            crop = cv2.copyMakeBorder(image[y1:y2, x1:x2], padding, padding, padding, padding,
                                     cv2.BORDER_CONSTANT, value=(0, 0, 0))
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            items = sorted(reader.readtext(crop, detail=1, paragraph=False),
                           key=lambda item: float(item[0][0][0]))
            field["raw_text"] = " ".join(str(item[1]).strip() for item in items).strip()
            field["confidence"] = min((float(item[2]) for item in items), default=None)
            if field["confidence"] is None or field["confidence"] < minimum_confidence:
                raise ValueError("Remaining counter OCR is missing or below the confidence threshold")
            match = re.fullmatch(str(definition["valuePattern"]), field["raw_text"], flags=re.IGNORECASE)
            if match is None:
                raise ValueError("OCR does not match the taught Remaining counter pattern")
            field["value"] = int(match.group(1))
            if field["value"] < 0:
                raise ValueError("Remaining counter cannot be negative")
        except Exception as error:
            field.update(value=None, error=str(error))
    return fields


def get_daily_events_dialog_info(target: dict[str, Any], *, send_key: Callable[[int, str], bool],
                                 dialog_timeout_seconds: float = 10.0,
                                 close_timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Open Daily Events if needed, read five counters, and close its verified dialog."""
    import win32gui

    result: dict[str, Any] = {"success": False, "target": dict(target)}
    dialog_verified = False
    try:
        hwnd = int(target["hwnd"])
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            raise RuntimeError("Selected game window is no longer visible")
        layout = json.loads(TEACHING_PATH.read_text(encoding="utf-8-sig"))["dialogs"]["dialog.advanced.opened"]["layout"]
        anchor = layout["Anchor"]
        template = _load_template(PROJECT_ROOT / str(anchor["titleImagePath"]))
        threshold = float(anchor["templateThreshold"])
        if not 0 < threshold <= 1 or float(template.std()) < 1e-6:
            raise ValueError("Invalid Daily Events title template or threshold")
        capture = GameWindowCapture()
        image = capture.capture(hwnd)
        if image is None:
            raise RuntimeError("Could not capture the selected game window")
        title = _match(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), template, "Daily Events title")
        result["dialog_already_open"] = title["score"] >= threshold
        if not result["dialog_already_open"]:
            key = str(layout["openKey"])
            if len(key) != 1 or not send_key(hwnd, key):
                raise RuntimeError("Could not send the configured Daily Events opening key")
            result["action"] = {"key": key, "delivery": "window_message"}
            deadline = time.monotonic() + dialog_timeout_seconds
            while time.monotonic() < deadline:
                image = capture.capture(hwnd)
                if image is not None:
                    title = _match(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), template, "Daily Events title")
                    if title["score"] >= threshold:
                        break
                time.sleep(0.05)
            else:
                raise RuntimeError("Daily Events title was not matched after the opening key")
        dialog_verified = True
        result["verification"] = {"success": True, "method": "template_matching", "score": title["score"],
                                  "threshold": threshold, "bbox": title["bbox"]}
        fields = _read_remaining(image, title, layout)
        result["fields"] = fields
        result["remaining"] = {key: field["value"] for key, field in fields.items()}
        result["missing_fields"] = [key for key, field in fields.items() if field["value"] is None]
        result["success"] = not result["missing_fields"]
        if not result["success"]:
            result["error"] = "Could not read Daily Events counters: " + ", ".join(result["missing_fields"])
    except Exception as error:
        result.update(success=False, error=str(error))
    finally:
        if dialog_verified:
            try:
                closing = close_taught_dialog(hwnd, layout, template, threshold, close_timeout_seconds, "Daily Events")
            except Exception as error:
                closing = {"closed": False, "error": str(error)}
            result["dialog_close"] = closing
            if not closing["closed"]:
                result["success"] = False
                result["error"] = "; ".join(filter(None, (result.get("error"), closing["error"])))
    return result
