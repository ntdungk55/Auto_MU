"""Read companion details from image-verified Manage Sub-Characters teaching."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import cv2

from src.ai_control.companion_switcher import (
    PROJECT_ROOT, TEACHING_PATH, GameWindowCapture, MouseController,
    _load_template, _match, _open_button_center, get_companion_summoned_state,
)
from src.ai_control.dialog_actions import close_taught_dialog
from src.logic.system_executor.ocr_engine import EasyOCREngine, WinRTOCREngine


def _read_fields(image: Any, title: dict[str, Any], layout: dict[str, Any]) -> dict[str, Any]:
    """OCR configured value rectangles relative to the matched title on this frame."""
    settings = layout["textRecognition"]
    default_scale, default_padding = float(settings["scale"]), int(settings["padding"])
    minimum_confidence = float(settings["minimumConfidence"])
    if not 1 <= default_scale <= 8 or not 0 <= default_padding <= 32 or not 0 <= minimum_confidence <= 1:
        raise ValueError("Invalid companion textRecognition settings")
    if settings["engine"] != "winrt" or settings["fallbackEngine"] != "easyocr":
        raise ValueError("Companion OCR requires winrt with easyocr fallback")
    engine = WinRTOCREngine()
    fields: dict[str, Any] = {}
    for field, key in (("name", "characterName"), ("server", "server"), ("map", "map"),
                       ("level", "level"), ("reset", "reset"), ("status", "status")):
        region = layout["textRegions"][key]
        relative = region["roiRelativeToTitle"]
        scale = float(region.get("scale", default_scale))
        padding = int(region.get("padding", default_padding))
        allowlist = region.get("allowlist")
        if not 1 <= scale <= 8 or not 0 <= padding <= 32:
            raise ValueError(f"Invalid companion {field} OCR scale or padding")
        if allowlist is not None and (not isinstance(allowlist, str) or not allowlist):
            raise ValueError(f"Invalid companion {field} OCR allowlist")
        roi = {axis: int(relative[axis]) + int(title["bbox"][axis[0] + "1"])
               for axis in ("x1", "y1", "x2", "y2")}
        x1, y1, x2, y2 = (roi[axis] for axis in ("x1", "y1", "x2", "y2"))
        if not (0 <= x1 < x2 <= image.shape[1] and 0 <= y1 < y2 <= image.shape[0]):
            raise ValueError(f"Companion {field} ROI lies outside the captured image: {roi}")
        crop = cv2.copyMakeBorder(image[y1:y2, x1:x2], padding, padding, padding, padding,
                                  cv2.BORDER_CONSTANT, value=(0, 0, 0))
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        raw = " ".join(engine.recognize(crop).split())
        method, confidence = "winrt", None
        if not raw:
            reader = EasyOCREngine()._get_reader()
            easyocr_options: dict[str, Any] = {"detail": 1, "paragraph": False}
            if allowlist is not None:
                easyocr_options["allowlist"] = allowlist
            items = [] if reader is None else reader.readtext(crop, **easyocr_options)
            accepted = sorted((item for item in items if float(item[2]) >= minimum_confidence),
                              key=lambda item: float(item[0][0][0]))
            raw = " ".join(str(item[1]).strip() for item in accepted).strip()
            method = "easyocr"
            confidence = min((float(item[2]) for item in accepted), default=None)
        value = raw or None
        if field == "level" and value:
            # Only correct O in the numeric level position; preserve raw OCR evidence.
            value = re.sub(r"^[oO](?=[.,]mt\b)", "0", value)
        fields[field] = {"value": value, "raw_text": raw, "method": method,
                         "confidence": confidence, "roi": roi}
    return fields


def get_companion_information(target: dict[str, Any], *, dialog_timeout_seconds: float = 3.0,
                              close_timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Read six taught companion fields, then close the verified dialog using its X button."""
    import win32gui

    result: dict[str, Any] = {"success": False, "target": dict(target), "character": None}
    dialog_verified = False
    try:
        hwnd = int(target["hwnd"])
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            raise RuntimeError("Selected game window is no longer visible")
        layout = json.loads(TEACHING_PATH.read_text(encoding="utf-8-sig"))["dialogs"]["dialog.companion_management.opened"]["layout"]
        anchor = layout["Anchor"]
        threshold = float(anchor["templateThreshold"])
        template = _load_template(PROJECT_ROOT / str(anchor["titleImagePath"]))
        if not 0 < threshold <= 1 or float(template.std()) < 1e-6:
            raise ValueError("Invalid companion title template or threshold")
        capture = GameWindowCapture()
        image = capture.capture(hwnd)
        if image is None:
            raise RuntimeError("Could not capture the selected game window")
        title = _match(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), template, "Manage Sub-Characters title")
        already_open = title["score"] >= threshold
        result["dialog_already_open"] = already_open
        if not already_open:
            state = get_companion_summoned_state(hwnd)
            result.update(state)
            if state["companion_summoned"] is False:
                result.update(success=True, message="Companion slot 1 has not been summoned")
                return result
            if state["companion_summoned"] is not True:
                raise RuntimeError("Companion slot 1 state is uncertain; refusing to click")
            x, y = _open_button_center()
            MouseController(target_window_hwnd=hwnd).click_at_client(x, y)
            result["action"] = {"open_companion_management": {"x": x, "y": y}}
            deadline = time.monotonic() + dialog_timeout_seconds
            while time.monotonic() < deadline:
                image = capture.capture(hwnd)
                if image is not None:
                    title = _match(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), template, "Manage Sub-Characters title")
                    if title["score"] >= threshold:
                        break
                time.sleep(0.05)
            else:
                raise RuntimeError("Manage Sub-Characters title was not matched after opening slot 1")
        dialog_verified = True
        result["companion_summoned"] = True
        result["verification"] = {"method": "template_matching", "score": title["score"],
                                  "threshold": threshold, "bbox": title["bbox"]}
        fields = _read_fields(image, title, layout)
        result["fields"] = fields
        result["character"] = {key: field["value"] for key, field in fields.items()}
        result["missing_fields"] = [key for key, field in fields.items() if field["value"] is None]
        result["success"] = not result["missing_fields"]
        if not result["success"]:
            result["error"] = "Could not read all companion fields: " + ", ".join(result["missing_fields"])
    except Exception as error:
        result.update(success=False, error=str(error))
    finally:
        if dialog_verified:
            try:
                closing = close_taught_dialog(hwnd, layout, template, threshold, close_timeout_seconds, "Manage Sub-Characters")
            except Exception as error:
                closing = {"closed": False, "error": str(error)}
            result["dialog_close"] = closing
            if not closing["closed"]:
                result["success"] = False
                result["error"] = "; ".join(filter(None, (result.get("error"), closing["error"])))
    return result
