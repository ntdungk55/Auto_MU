"""Read and control the taught Auto Z and Autoplay Management states."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

import cv2

from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control.companion_switcher import PROJECT_ROOT, TEACHING_PATH, _match
from src.logic.system_executor.mouse_controller import MouseController


STATE_CHANGE_TIMEOUT_SECONDS = 2.0
DIALOG_TIMEOUT_SECONDS = 2.0


def _config() -> dict[str, Any]:
    return json.loads(TEACHING_PATH.read_text(encoding="utf-8-sig"))


def _capture(hwnd: int) -> Any:
    image = GameWindowCapture().capture(hwnd)
    if image is None:
        raise RuntimeError("Could not capture the selected game window")
    return image


def _wake_target(hwnd: int) -> None:
    """Dismiss the game power-saving overlay before any taught-icon capture."""
    import win32con
    import win32gui

    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        raise RuntimeError("Selected game window is no longer visible")
    # Client coordinate (1, 1) is intentionally outside all taught game controls.
    lparam = (1 << 16) | 1
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)
    time.sleep(0.1)


def _load_template(path: str) -> Any:
    template = cv2.imread(str(PROJECT_ROOT / path), cv2.IMREAD_GRAYSCALE)
    if template is None or template.size == 0:
        raise FileNotFoundError(f"Could not read taught template: {path}")
    return template


def _state_from_templates(image: Any, roi: dict[str, Any], templates: dict[str, Any], *,
                          icon_roi_relative: dict[str, Any] | None = None,
                          edge_matching: bool = False,
                          threshold_override: float | None = None) -> dict[str, Any]:
    x1, y1, x2, y2 = (int(roi[axis]) for axis in ("x1", "y1", "x2", "y2"))
    if not (0 <= x1 < x2 <= image.shape[1] and 0 <= y1 < y2 <= image.shape[0]):
        raise ValueError("The taught state ROI lies outside the captured window")
    crop = cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    if icon_roi_relative is not None:
        ix1, iy1, ix2, iy2 = (int(icon_roi_relative[axis]) for axis in ("x1", "y1", "x2", "y2"))
        if not (0 <= ix1 < ix2 <= crop.shape[1] and 0 <= iy1 < iy2 <= crop.shape[0]):
            raise ValueError("The taught central icon ROI lies outside its control")
        crop = crop[iy1:iy2, ix1:ix2]
        x1, y1, x2, y2 = x1 + ix1, y1 + iy1, x1 + ix2, y1 + iy2
    if edge_matching:
        crop = cv2.Canny(cv2.GaussianBlur(crop, (3, 3), 0), 35, 100)
    scores: dict[str, float] = {}
    for state, definition in templates.items():
        template = _load_template(str(definition["path"]))
        if edge_matching:
            template = cv2.Canny(cv2.GaussianBlur(template, (3, 3), 0), 35, 100)
        if template.shape[0] > crop.shape[0] or template.shape[1] > crop.shape[1]:
            scores[state] = -1.0
            continue
        _, score, _, _ = cv2.minMaxLoc(cv2.matchTemplate(crop, template, cv2.TM_CCOEFF_NORMED))
        scores[state] = round(float(score), 6)
    state = max(scores, key=scores.get, default="")
    threshold = float(threshold_override if threshold_override is not None else templates.get(state, {}).get("threshold", 1.0))
    runner_up = max((score for name, score in scores.items() if name != state), default=-1.0)
    score_margin = round(scores.get(state, -1.0) - runner_up, 6)
    minimum_margin = float(next(iter(templates.values()), {}).get("minimumScoreMargin", 0.05))
    return {
        "state": state if state and scores[state] >= threshold and score_margin >= minimum_margin else None,
        "scores": scores,
        "threshold": threshold,
        "score_margin": score_margin,
        "minimum_score_margin": minimum_margin,
        "roi": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
    }


def _main_state(hwnd: int, control_name: str) -> dict[str, Any]:
    control = _config()["mainInfo"][control_name]
    result = _state_from_templates(
        _capture(hwnd), control["roi"], control["stateTemplates"],
        icon_roi_relative=control.get("iconRoiRelative"),
        edge_matching=bool(control.get("edgeMatching", False)),
        threshold_override=control.get("edgeThreshold"),
    )
    result["control"] = control_name
    return result


def _click_client(hwnd: int, x: int, y: int) -> None:
    """Use a real click because these HUD controls ignore background window messages."""
    import win32api
    import win32con
    import win32gui
    import win32process

    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        raise RuntimeError("Selected game window is no longer visible")
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        current_thread = win32api.GetCurrentThreadId()
        foreground = win32gui.GetForegroundWindow()
        threads = {win32process.GetWindowThreadProcessId(hwnd)[0],
                   win32process.GetWindowThreadProcessId(foreground)[0]}
        try:
            for thread in threads:
                if thread and thread != current_thread:
                    win32process.AttachThreadInput(current_thread, thread, True)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            for thread in threads:
                if thread and thread != current_thread:
                    try:
                        win32process.AttachThreadInput(current_thread, thread, False)
                    except Exception:
                        pass
    if win32gui.GetForegroundWindow() != hwnd:
        raise RuntimeError("Could not focus the selected game window for the required HUD click")
    screen_x, screen_y = win32gui.ClientToScreen(hwnd, (int(x), int(y)))
    MouseController(target_window_hwnd=hwnd).click_at_with_marker(screen_x, screen_y)


def _click_roi_center(hwnd: int, roi: dict[str, Any]) -> dict[str, int]:
    x = (int(roi["x1"]) + int(roi["x2"])) // 2
    y = (int(roi["y1"]) + int(roi["y2"])) // 2
    _click_client(hwnd, x, y)
    return {"x": x, "y": y}


def _wait_for_state(hwnd: int, control_name: str, expected: str) -> dict[str, Any]:
    deadline = time.monotonic() + STATE_CHANGE_TIMEOUT_SECONDS
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = _main_state(hwnd, control_name)
        if last["state"] == expected:
            return last
        time.sleep(0.05)
    return last


def set_main_character_auto_z(target: dict[str, Any], running: bool) -> dict[str, Any]:
    """Ensure Auto Z is running or stopped and verify its taught icon changed."""
    target_result = dict(target)
    try:
        hwnd = int(target_result["hwnd"])
        _wake_target(hwnd)
        expected = "running" if running else "stopped"
        before = _main_state(hwnd, "autoState")
        if before["state"] is None:
            raise RuntimeError("Could not identify the Auto Z state from its taught icons")
        if before["state"] == expected:
            return {"success": True, "target": target_result, "state": expected, "changed": False, "before": before}
        click = _click_roi_center(hwnd, _config()["mainInfo"]["autoState"]["roi"])
        after = _wait_for_state(hwnd, "autoState", expected)
        if after.get("state") != expected:
            return {"success": False, "target": target_result, "before": before, "after": after,
                    "click": click, "error": "Auto Z icon did not change after clicking; the game may block this action."}
        return {"success": True, "target": target_result, "state": expected, "changed": True,
                "before": before, "after": after, "click": click}
    except Exception as error:
        return {"success": False, "target": target_result, "error": str(error)}


def _find_autoplay_dialog(image: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    layout = _config()["dialogs"]["dialog.autoplay_management.opened"]["layout"]
    anchor = layout["Anchor"]
    title = _match(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _load_template(str(anchor["titleImagePath"])), "Autoplay Management title")
    if title["score"] < float(anchor["templateThreshold"]):
        return layout, title, {"score": 0.0}
    button = layout["buttons"]["saveAndStart"]
    relative = button["roiRelativeToTitle"]
    bbox = title["bbox"]
    x1, y1 = int(bbox["x1"]) + int(relative["x1"]), int(bbox["y1"]) + int(relative["y1"])
    x2, y2 = int(bbox["x1"]) + int(relative["x2"]), int(bbox["y1"]) + int(relative["y2"])
    search = cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    template = _load_template(str(button["templateImagePath"]))
    match = _match(search, template, "Save and Start")
    for axis in ("x1", "x2"):
        match["bbox"][axis] += x1
    for axis in ("y1", "y2"):
        match["bbox"][axis] += y1
    match["center"] = {"x": (match["bbox"]["x1"] + match["bbox"]["x2"]) // 2,
                       "y": (match["bbox"]["y1"] + match["bbox"]["y2"]) // 2}
    return layout, title, match


def _wait_for_autoplay_dialog(hwnd: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    deadline = time.monotonic() + DIALOG_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        result = _find_autoplay_dialog(_capture(hwnd))
        layout, title, button = result
        if title["score"] >= float(layout["Anchor"]["templateThreshold"]) and button["score"] >= float(layout["buttons"]["saveAndStart"]["templateThreshold"]):
            return result
        time.sleep(0.05)
    return None


def start_autoplay_management(target: dict[str, Any]) -> dict[str, Any]:
    """Start Autoplay Management through its verified dialog and Save and Start button."""
    target_result = dict(target)
    try:
        hwnd = int(target_result["hwnd"])
        _wake_target(hwnd)
        before = _main_state(hwnd, "autoPlayManagement")
        if before["state"] is None:
            raise RuntimeError("Could not identify the Autoplay Management state from its taught icons")
        control_roi = _config()["mainInfo"]["autoPlayManagement"]["roi"]
        stop_click = None
        if before["state"] == "running":
            stop_click = _click_roi_center(hwnd, control_roi)
            stopped = _wait_for_state(hwnd, "autoPlayManagement", "stopped")
            if stopped.get("state") != "stopped":
                return {"success": False, "target": target_result, "before": before, "after": stopped,
                        "click": stop_click, "error": "Autoplay Management did not stop after clicking."}
        open_click = _click_roi_center(hwnd, control_roi)
        dialog = _wait_for_autoplay_dialog(hwnd)
        if dialog is None:
            return {"success": False, "target": target_result, "before": before, "click": open_click,
                    "error": "Autoplay Management dialog title or Save and Start button was not verified."}
        _, title, save = dialog
        _click_client(hwnd, save["center"]["x"], save["center"]["y"])
        after = _wait_for_state(hwnd, "autoPlayManagement", "running")
        if after.get("state") != "running":
            return {"success": False, "target": target_result, "before": before, "after": after,
                    "dialog": {"title": title, "save_and_start": save},
                    "error": "Autoplay Management did not start after Save and Start."}
        return {"success": True, "target": target_result, "state": "running", "changed": True,
                "before": before, "after": after, "stop_click": stop_click, "open_click": open_click,
                "dialog": {"title": title, "save_and_start": save}}
    except Exception as error:
        return {"success": False, "target": target_result, "error": str(error)}


def get_companion_training_state(target: dict[str, Any]) -> dict[str, Any]:
    """Return whether slot-1 companion shows the taught training play icon."""
    target_result = dict(target)
    try:
        hwnd = int(target_result["hwnd"])
        _wake_target(hwnd)
        config = _config()["mainInfo"]["companionManagement1"]
        result = _state_from_templates(
            _capture(hwnd), config["roi"], config["trainingStateTemplates"],
            icon_roi_relative=config.get("trainingIconRoiRelative"),
            edge_matching=bool(config.get("edgeMatching", False)),
            threshold_override=config.get("edgeThreshold"),
        )
        if result["state"] is None:
            return {"success": False, "target": target_result, **result,
                    "error": "Could not identify the companion training icon."}
        return {"success": True, "target": target_result, **result}
    except Exception as error:
        return {"success": False, "target": target_result, "error": str(error)}
