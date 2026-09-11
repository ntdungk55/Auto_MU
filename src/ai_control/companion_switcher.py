"""Switch the selected MU window into its first displayed companion character."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

import cv2

from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.logic.system_executor.mouse_controller import MouseController


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEACHING_PATH = PROJECT_ROOT / "mcp" / "config" / "mu_game_window.json"
TITLE_TEMPLATE_RECT = (163, 28, 300, 55)
ENTER_CHARACTER_TEMPLATE_RECT = (221, 238, 331, 271)
ENTER_FROM_TITLE_OFFSET = (ENTER_CHARACTER_TEMPLATE_RECT[0] - TITLE_TEMPLATE_RECT[0], ENTER_CHARACTER_TEMPLATE_RECT[1] - TITLE_TEMPLATE_RECT[1])
ENTER_MINIMUM_SCORE = 0.65
ENTER_MATCH_MARGIN = 18


def _load_dialog_templates(reference_image: Path | None = None) -> tuple[Any, Any, float]:
    """Load the configured title image and button template, with an optional screenshot override."""
    payload = json.loads(TEACHING_PATH.read_text(encoding="utf-8-sig"))
    layout = payload["dialogs"]["dialog.companion_management.opened"]["layout"]
    anchor = layout["Anchor"]
    threshold = float(anchor["templateThreshold"])
    if not 0.0 < threshold <= 1.0:
        raise ValueError("dialog title templateThreshold must be greater than 0 and at most 1")
    if reference_image is None:
        title_template = _load_template(PROJECT_ROOT / str(anchor["titleImagePath"]))
        enter_template = _load_template(PROJECT_ROOT / str(layout["buttons"]["enterCharacter"]["templateImagePath"]))
    else:
        title_template = _load_template(reference_image, TITLE_TEMPLATE_RECT)
        enter_template = _load_template(reference_image, ENTER_CHARACTER_TEMPLATE_RECT)
    return title_template, enter_template, threshold


def _open_button_center() -> tuple[int, int]:
    payload = json.loads(TEACHING_PATH.read_text(encoding="utf-8-sig"))
    roi = payload["mainInfo"]["companionManagement1"]["roi"]
    return ((int(roi["x1"]) + int(roi["x2"])) // 2, (int(roi["y1"]) + int(roi["y2"])) // 2)


def get_companion_summoned_state(hwnd: int) -> dict[str, Any]:
    """Return whether the slot-1 icon confirms a companion has been summoned."""
    payload = json.loads(TEACHING_PATH.read_text(encoding="utf-8-sig"))
    config = payload["mainInfo"]["companionManagement1"]
    roi = config["roi"]
    template_path = PROJECT_ROOT / str(config["notSummonedTemplate"])
    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise FileNotFoundError(f"Could not read not-summoned companion template: {template_path}")
    image = GameWindowCapture().capture(hwnd)
    if image is None:
        raise RuntimeError("Could not capture the selected game window for companion state verification")
    x1, y1, x2, y2 = (int(roi[key]) for key in ("x1", "y1", "x2", "y2"))
    button = cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    if button.shape != template.shape:
        raise RuntimeError(f"Companion button ROI has unexpected size {button.shape}; expected {template.shape}")
    score = float(cv2.matchTemplate(button, template, cv2.TM_CCOEFF_NORMED)[0][0])
    threshold = float(config["notSummonedThreshold"])
    return {
        "companion_summoned": score < threshold,
        "not_summoned_icon_score": round(score, 6),
        "not_summoned_threshold": threshold,
    }


def _load_template(reference: Path, rect: tuple[int, int, int, int] | None = None) -> Any:
    image = cv2.imread(str(reference), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Could not read companion dialog reference image: {reference}")
    if rect is None:
        return image
    x1, y1, x2, y2 = rect
    return image[y1:y2, x1:x2]


def _match(image: Any, template: Any, name: str) -> dict[str, Any]:
    _, score, _, top_left = cv2.minMaxLoc(cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED))
    x, y = int(top_left[0]), int(top_left[1])
    height, width = template.shape
    return {"name": name, "score": round(float(score), 6), "bbox": {"x1": x, "y1": y, "x2": x + width, "y2": y + height}, "center": {"x": x + width // 2, "y": y + height // 2}}


def _match_enter_near_title(image: Any, template: Any, title_match: dict[str, Any]) -> dict[str, Any]:
    expected_x = int(title_match["bbox"]["x1"]) + ENTER_FROM_TITLE_OFFSET[0]
    expected_y = int(title_match["bbox"]["y1"]) + ENTER_FROM_TITLE_OFFSET[1]
    height, width = template.shape
    x1, y1 = max(0, expected_x - ENTER_MATCH_MARGIN), max(0, expected_y - ENTER_MATCH_MARGIN)
    x2, y2 = min(image.shape[1], expected_x + width + ENTER_MATCH_MARGIN), min(image.shape[0], expected_y + height + ENTER_MATCH_MARGIN)
    if x2 - x1 < width or y2 - y1 < height:
        return {"name": "enterCharacter", "score": 0.0, "center": {"x": expected_x + width // 2, "y": expected_y + height // 2}}
    match = _match(image[y1:y2, x1:x2], template, "enterCharacter")
    for key in ("x1", "x2"):
        match["bbox"][key] += x1
    for key in ("y1", "y2"):
        match["bbox"][key] += y1
    match["center"] = {"x": (match["bbox"]["x1"] + match["bbox"]["x2"]) // 2, "y": (match["bbox"]["y1"] + match["bbox"]["y2"]) // 2}
    return match


def _wait_for_dialog(hwnd: int, title_template: Any, enter_template: Any, timeout_seconds: float, title_threshold: float) -> tuple[dict[str, Any], dict[str, Any]]:
    capture = GameWindowCapture()
    deadline = time.monotonic() + timeout_seconds
    last_title: dict[str, Any] | None = None
    last_enter: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        image = capture.capture(hwnd)
        if image is not None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            last_title = _match(gray, title_template, "Manage Sub-Characters title")
            last_enter = _match_enter_near_title(gray, enter_template, last_title)
            if last_title["score"] >= title_threshold and last_enter["score"] >= ENTER_MINIMUM_SCORE:
                return last_title, last_enter
        time.sleep(0.05)
    raise RuntimeError(f"Companion dialog was not matched: title={last_title}, enterCharacter={last_enter}")


def _wait_for_title_change(hwnd: int, title_before: str, timeout_seconds: float) -> str:
    import win32gui

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        title_after = win32gui.GetWindowText(hwnd)
        if title_after != title_before:
            return title_after
        time.sleep(0.05)
    return title_before


def open_companion_management_dialog(target: dict[str, Any], *, reference_image: Path | None = None, dialog_timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Open and verify Companion Management without entering another character."""
    import win32gui

    target_result = dict(target)
    try:
        hwnd = int(target_result["hwnd"])
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            return {"success": False, "target": target_result, "error": "Selected game window is no longer visible"}
        title_template, enter_template, title_threshold = _load_dialog_templates(reference_image)
        companion_state = get_companion_summoned_state(hwnd)
        if not companion_state["companion_summoned"]:
            return {
                "success": False,
                "target": target_result,
                "precondition": companion_state,
                "error": "Companion slot 1 has not been summoned",
            }
        open_x, open_y = _open_button_center()
        mouse = MouseController(target_window_hwnd=hwnd)
        mouse.click_at_client(open_x, open_y)
        title_match, enter_match = _wait_for_dialog(hwnd, title_template, enter_template, dialog_timeout_seconds, title_threshold)
        return {
            "success": True, "target": target_result, "precondition": companion_state,
            "action": {"open_companion_management": {"x": open_x, "y": open_y},
                       "delivery": "window_message_without_focus"},
            "matches": {"title": title_match, "enterCharacter": enter_match},
            "verification": {"success": True, "event_type": "dialog.companion_management.opened",
                             "method": "template_matching", "score": title_match["score"],
                             "threshold": title_threshold},
        }
    except Exception as error:
        return {"success": False, "target": target_result, "error": str(error)}


def switch_to_companion_character(target: dict[str, Any], *, reference_image: Path | None = None, dialog_timeout_seconds: float = 2.0, verify_timeout_seconds: float = 3.0) -> dict[str, Any]:
    """Open the configured dialog, enter its companion, and verify the window title changes."""
    import win32gui

    result = open_companion_management_dialog(
        target, reference_image=reference_image, dialog_timeout_seconds=dialog_timeout_seconds,
    )
    if not result["success"]:
        return result
    try:
        hwnd = int(target["hwnd"])
        title_before = win32gui.GetWindowText(hwnd)
        center = result["matches"]["enterCharacter"]["center"]
        MouseController(target_window_hwnd=hwnd).click_at_client(int(center["x"]), int(center["y"]))
        title_after = _wait_for_title_change(hwnd, title_before, verify_timeout_seconds)
        result["action"]["enter_character"] = center
        result["verification"] = {"title_before": title_before, "title_after": title_after}
        result["success"] = title_after != title_before
        if not result["success"]:
            result["error"] = "Game window title did not change after entering the companion"
    except Exception as error:
        result.update(success=False, error=str(error))
    return result
