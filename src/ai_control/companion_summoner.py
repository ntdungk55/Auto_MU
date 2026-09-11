"""Shared companion-summoning flow for MCP and manual scripts."""

from __future__ import annotations

import json
from pathlib import Path
import re
import time
from typing import Any

import cv2

from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control.companion_switcher import _open_button_center, get_companion_summoned_state
from src.logic.system_executor.mouse_controller import MouseController
from src.logic.system_executor.ocr_engine import EasyOCREngine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEACHING_PATH = PROJECT_ROOT / "mcp" / "config" / "mu_game_window.json"



def _character_list_config() -> dict[str, Any]:
    """Load the complete Character List teaching configuration."""
    configuration = json.loads(TEACHING_PATH.read_text(encoding="utf-8"))
    return configuration["dialogs"]["dialog.character_list.opened"]


def _title_search_roi() -> tuple[int, int, int, int]:
    """Return the configured Character List title search ROI."""
    roi = _character_list_config()["roi"]
    return int(roi["x1"]), int(roi["y1"]), int(roi["x2"]), int(roi["y2"])


def _title_anchor_config() -> dict[str, Any]:
    """Return teaching data for the Character List title anchor."""
    return _character_list_config()["layout"]["Anchor"]


def _title_template_path() -> Path:
    """Return the configured title-template path resolved from the project root."""
    return PROJECT_ROOT / str(_title_anchor_config()["titleImagePath"])


def _title_template_match(image: Any) -> dict[str, Any]:
    template = cv2.imread(str(_title_template_path()), cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise FileNotFoundError(f"Could not read Character List title image: {_title_template_path()}")
    if float(template.std()) < 1e-6:
        raise ValueError("Character List title image must contain visual detail")
    x1, y1, x2, y2 = _title_search_roi()
    search = cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    if template.shape[0] > search.shape[0] or template.shape[1] > search.shape[1]:
        raise ValueError("Character List title image is larger than its search ROI")
    _, score, _, top_left = cv2.minMaxLoc(cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED))
    tx, ty = int(top_left[0]) + x1, int(top_left[1]) + y1
    height, width = template.shape
    return {
        "score": round(float(score), 6),
        "bbox": {"x1": tx, "y1": ty, "x2": tx + width, "y2": ty + height},
    }


def _character_list_relative_roi() -> tuple[int, int, int, int]:
    """Return the character-list ROI relative to the title anchor from teaching JSON."""
    roi = _character_list_config()["layout"]["textRegions"]["characterList"]["roi"]
    return int(roi["x1"]), int(roi["y1"]), int(roi["x2"]), int(roi["y2"])


def _character_list_close_roi() -> tuple[int, int, int, int]:
    """Return the close-button ROI relative to the Character List title anchor."""
    roi = _character_list_config()["layout"]["buttons"]["close"]["roi"]
    return int(roi["x1"]), int(roi["y1"]), int(roi["x2"]), int(roi["y2"])


def _close_character_list(hwnd: int, title_bbox: dict[str, int]) -> dict[str, int]:
    """Post a no-focus click to the configured Character List close button."""
    relative_x1, relative_y1, relative_x2, relative_y2 = _character_list_close_roi()
    x1 = int(title_bbox["x1"]) + relative_x1
    y1 = int(title_bbox["y1"]) + relative_y1
    x2 = int(title_bbox["x1"]) + relative_x2
    y2 = int(title_bbox["y1"]) + relative_y2
    click_x, click_y = (x1 + x2) // 2, (y1 + y2) // 2
    MouseController(target_window_hwnd=hwnd).click_at_client(click_x, click_y)
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "click_x": click_x, "click_y": click_y}


def _read_character_list(image: Any, title_bbox: dict[str, int]) -> dict[str, Any]:
    """OCR the configured character-list region and report absolute and title-relative boxes."""
    relative_x1, relative_y1, relative_x2, relative_y2 = _character_list_relative_roi()
    x1 = int(title_bbox["x1"]) + relative_x1
    y1 = int(title_bbox["y1"]) + relative_y1
    x2 = int(title_bbox["x1"]) + relative_x2
    y2 = int(title_bbox["y1"]) + relative_y2
    height, width = image.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(width, x2), min(height, y2)
    if x1 >= x2 or y1 >= y2:
        raise RuntimeError("Configured Character List ROI is outside the captured game client")
    reader = EasyOCREngine()._get_reader()
    if reader is None:
        raise RuntimeError("EasyOCR reader is unavailable")
    items: list[dict[str, Any]] = []
    for bbox, text, confidence in reader.readtext(image[y1:y2, x1:x2], detail=1, decoder="greedy"):
        points = [(round(float(point[0])) + x1, round(float(point[1])) + y1) for point in bbox]
        absolute_bbox = {
            "x1": min(point[0] for point in points),
            "y1": min(point[1] for point in points),
            "x2": max(point[0] for point in points),
            "y2": max(point[1] for point in points),
        }
        items.append(
            {
                "text": str(text),
                "confidence": round(float(confidence), 4),
                "bbox": absolute_bbox,
                "bbox_relative_to_title": {
                    "x1": absolute_bbox["x1"] - int(title_bbox["x1"]),
                    "y1": absolute_bbox["y1"] - int(title_bbox["y1"]),
                    "x2": absolute_bbox["x2"] - int(title_bbox["x1"]),
                    "y2": absolute_bbox["y2"] - int(title_bbox["y1"]),
                },
            }
        )
    return {
        "roi": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        "roi_relative_to_title": {
            "x1": relative_x1,
            "y1": relative_y1,
            "x2": relative_x2,
            "y2": relative_y2,
        },
        "items": items,
    }


def _normalize_character_name(value: str) -> str:
    """Normalize a MU character name while preserving non-equivalent OCR characters."""
    return re.sub(r"\s+", "", value).upper().replace("O", "0")


def _find_target_character(character_list: dict[str, Any], target_character: str) -> dict[str, Any] | None:
    """Return the sole OCR item whose normalized text exactly equals the target name."""
    normalized_target = _normalize_character_name(target_character)
    matches = [
        item
        for item in character_list["items"]
        if _normalize_character_name(str(item["text"])) == normalized_target
    ]
    return matches[0] if len(matches) == 1 else None


def _wait_for_companion_summon(hwnd: int, timeout_seconds: float) -> dict[str, Any] | None:
    """Poll the slot-1 icon until it confirms that a companion is summoned."""
    deadline = time.monotonic() + max(0.1, timeout_seconds)
    while time.monotonic() < deadline:
        companion_state = get_companion_summoned_state(hwnd)
        if companion_state["companion_summoned"]:
            return companion_state
        time.sleep(0.05)
    return None


def summon_companion_character(
    target: dict[str, Any], target_character: str, *,
    dialog_timeout_seconds: float = 3.0, verify_timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Summon one OCR-selected companion on the caller's window and verify its slot icon."""
    import win32gui

    result: dict[str, Any] = {"success": False, "target": dict(target)}
    try:
        if not isinstance(target_character, str) or not target_character.strip():
            raise ValueError("target_character must be a non-empty character name")
        hwnd = int(target["hwnd"])
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            raise RuntimeError("Selected game window is no longer visible")
        if not _title_template_path().is_file():
            raise FileNotFoundError(f"Character List title image does not exist: {_title_template_path()}")
        threshold = float(_title_anchor_config()["templateThreshold"])
        if not 0.0 < threshold <= 1.0:
            raise ValueError("Character List templateThreshold must be greater than 0 and at most 1")
        state = get_companion_summoned_state(hwnd)
        result["before_companion_state"] = state
        if state["companion_summoned"]:
            raise RuntimeError("Companion is already summoned")
        x, y = _open_button_center()
        mouse = MouseController(target_window_hwnd=hwnd)
        mouse.click_at_client(x, y)
        capture = GameWindowCapture()
        deadline = time.monotonic() + max(0.1, float(dialog_timeout_seconds))
        while time.monotonic() < deadline:
            image = capture.capture(hwnd)
            if image is None:
                time.sleep(0.05)
                continue
            title_match = _title_template_match(image)
            result["title_match"] = title_match
            if title_match["score"] < threshold:
                time.sleep(0.05)
                continue
            try:
                character_list = _read_character_list(image, title_match["bbox"])
                result["character_list"] = character_list
                selected_item = _find_target_character(character_list, target_character)
                if selected_item is None:
                    raise RuntimeError(f"Target character was not uniquely found by OCR: {target_character}")
            except Exception:
                result["close_button"] = _close_character_list(hwnd, title_match["bbox"])
                result["dialog_close_requested"] = True
                raise
            bbox = selected_item["bbox"]
            mouse.click_at_client((bbox["x1"] + bbox["x2"]) // 2, (bbox["y1"] + bbox["y2"]) // 2)
            result["selected_character"] = selected_item
            result["after_companion_state"] = _wait_for_companion_summon(hwnd, float(verify_timeout_seconds))
            result["success"] = result["after_companion_state"] is not None
            if not result["success"]:
                result["error"] = "Companion slot icon still indicates not summoned after selecting the character"
            return result
        raise RuntimeError("Character List title was not detected")
    except Exception as error:
        result["error"] = str(error)
        return result
