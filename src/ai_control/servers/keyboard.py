"""MCP server exposing the existing Keyboard action to AI clients."""

from __future__ import annotations

import contextlib
import io
import traceback
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable

try:
    from mcp.server import FastMCP
except ImportError:  # MCP 2.x
    from mcp.server import MCPServer as FastMCP

from src.ai_control.companion_switcher import switch_to_companion_character as run_companion_switch
from src.ai_control.companion_switcher import verify_and_close_companion_management_dialog as run_open_companion_dialog
from src.ai_control.companion_info import get_companion_information
from src.ai_control.companion_summoner import summon_companion_character as run_companion_summon
from src.ai_control.current_character_info import get_current_character_map as read_current_character_map
from src.ai_control.daily_events_info import get_daily_events_dialog_info as read_daily_events
from src.ai_control.auto_play_control import (
    get_companion_training_state as read_companion_training_state,
    set_main_character_auto_z as set_auto_z_state,
    start_autoplay_management as run_start_autoplay_management,
)
from src.ai_control.servers.process import resolve_selected_process
from src.logic.action_type import ActionMode, ActionType, AutoAction


mcp = FastMCP("Auto_MU Keyboard Actions")

MAX_TEXT_LENGTH = 500
MAX_DELAY_SECONDS = 30.0
DEFAULT_DIALOG_VERIFY_TIMEOUT_MS = 10000
SPECIAL_KEYS = {
    "tab", "esc", "escape", "enter", "return", "space", "backspace",
    "delete", "del", "insert", "ins", "home", "end", "page up",
    "pageup", "page down", "pagedown", "up", "down", "left", "right",
    "shift", "ctrl", "alt", "caps lock", "capslock", "num lock",
    "numlock", "scroll lock", "scrolllock", "print screen", "printscreen",
    "pause", "menu", "windows", "win",
} | {f"f{index}" for index in range(1, 13)}


def _validate_value(value: str, text_input_enabled: bool) -> tuple[str, list[str]]:
    errors: list[str] = []
    normalized = str(value or "") if text_input_enabled else str(value or "").strip().lower()

    if not normalized:
        errors.append("value không được để trống")
        return normalized, errors

    if text_input_enabled:
        if len(normalized) > MAX_TEXT_LENGTH:
            errors.append(f"Chuỗi văn bản không được vượt quá {MAX_TEXT_LENGTH} ký tự")
        return normalized, errors

    if len(normalized) == 1 or normalized in SPECIAL_KEYS:
        return normalized, errors

    if "+" in normalized:
        parts = [part.strip() for part in normalized.split("+") if part.strip()]
        modifiers = {"ctrl", "alt", "shift", "windows", "win"}
        if len(parts) >= 2 and all(part in modifiers for part in parts[:-1]):
            final_key = parts[-1]
            if len(final_key) == 1 or final_key in SPECIAL_KEYS:
                return "+".join(parts), errors

    errors.append(f"Phím không được hỗ trợ: {value}")
    return normalized, errors


def _validate_delay(delay_seconds: float) -> tuple[float, list[str]]:
    try:
        delay = float(delay_seconds)
    except (TypeError, ValueError):
        return 0.0, ["delay_seconds phải là số"]
    if not 0.0 <= delay <= MAX_DELAY_SECONDS:
        return delay, [f"delay_seconds phải nằm trong khoảng 0-{MAX_DELAY_SECONDS:g}"]
    return delay, []


def _build_keyboard_action(
    name: str,
    value: str,
    text_input_enabled: bool,
    purpose: str,
    delay_seconds: float,
    goto_step_enabled: bool,
    goto_step_index: int,
) -> tuple[AutoAction | None, list[str]]:
    errors: list[str] = []
    clean_name = str(name or "").strip()
    if not clean_name:
        errors.append("name không được để trống")
    elif len(clean_name) > 120:
        errors.append("name không được vượt quá 120 ký tự")

    normalized_value, value_errors = _validate_value(value, bool(text_input_enabled))
    delay, delay_errors = _validate_delay(delay_seconds)
    errors.extend(value_errors)
    errors.extend(delay_errors)

    try:
        goto_index = int(goto_step_index)
    except (TypeError, ValueError):
        goto_index = -1
    if goto_index < 0:
        errors.append("goto_step_index không được âm")

    if errors:
        return None, errors

    action = AutoAction(
        name=clean_name,
        purpose=str(purpose or "").strip(),
        action_type=ActionType.KEYBOARD,
        mode=ActionMode.ACTIVE,
        value=normalized_value,
        text_input_enabled=bool(text_input_enabled),
        delay=delay,
        goto_step_enabled=bool(goto_step_enabled),
        goto_step_index=goto_index,
    )
    return action, []


def _action_to_json(action: AutoAction) -> dict[str, Any]:
    return {
        "name": action.name,
        "purpose": action.purpose,
        "action_type": action.action_type.value,
        "mode": action.mode.value,
        "value": action.value,
        "text_input_enabled": action.text_input_enabled,
        "delay": action.delay,
        "goto_step_enabled": action.goto_step_enabled,
        "goto_step_index": action.goto_step_index,
    }


def _selected_visible_windows() -> tuple[list[dict[str, Any]], str | None]:
    process, error = resolve_selected_process()
    if error:
        return [], error
    windows = [window for window in (process or {}).get("windows", []) if window.get("visible")]
    selected_window_hwnd = int((process or {}).get("selected_window_hwnd") or 0)
    if selected_window_hwnd:
        windows = [window for window in windows if int(window.get("hwnd", 0)) == selected_window_hwnd]
        if not windows:
            return [], "Selected game window is no longer visible; select it again in Gemini Chat"
    if not windows:
        return [], "Process đã chọn không có cửa sổ hiển thị"
    return windows, None


def _post_virtual_key(hwnd: int, virtual_key: int) -> bool:
    """Queue one virtual-key press and release without focusing the target window."""
    import win32api
    import win32con
    import win32gui

    scan_code = int(win32api.MapVirtualKey(virtual_key, 0)) & 0xFF
    down_lparam = 1 | (scan_code << 16)
    up_lparam = down_lparam | (1 << 30) | (1 << 31)
    win32gui.PostMessage(int(hwnd), win32con.WM_KEYDOWN, int(virtual_key), down_lparam)
    win32gui.PostMessage(int(hwnd), win32con.WM_KEYUP, int(virtual_key), up_lparam)
    return True


def _post_single_key(hwnd: int, key: str) -> bool:
    """Queue one character key press for a specific window without focusing it."""
    if len(key) != 1:
        return False

    import win32api

    key_scan = int(win32api.VkKeyScan(key))
    if key_scan == -1:
        return False
    return _post_virtual_key(hwnd, key_scan & 0xFF)


def _wake_selected_window(target: dict[str, Any]) -> dict[str, Any]:
    """Wake the selected game with one background click at client coordinate (1, 1)."""
    import win32con
    import win32gui

    hwnd = int(target["hwnd"])
    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        raise RuntimeError("Selected game window is no longer visible")
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width, height = int(right - left), int(bottom - top)
    if width <= 0 or height <= 0:
        raise RuntimeError("Selected game window has an invalid client area")
    x, y = 1, 1
    foreground_before = int(win32gui.GetForegroundWindow() or 0)
    lparam = (y << 16) | (x & 0xFFFF)
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)
    foreground_after = int(win32gui.GetForegroundWindow() or 0)
    return {
        "success": True, "method": "background_top_left_click", "hwnd": hwnd,
        "x": x, "y": y, "client_width": width, "client_height": height,
        "foreground_before": foreground_before, "foreground_after": foreground_after,
        "foreground_changed": foreground_after != foreground_before,
        "focus_requested": False, "key_sent": False, "delay_ms": 0,
    }


def _await_dynamic_text(hwnd: int, event_type: str, timeout_ms: int) -> dict[str, Any]:
    """Verify one configured dialog by title image or OCR until it matches or times out."""
    from samples.ai_game_controller.domain.game_target import GameTarget
    from samples.ai_game_controller.infrastructure.game_state_reader import GameStateReader
    from samples.ai_game_controller.infrastructure.easyocr_recognizer import EasyOCRRecognizer
    from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture

    timeout_seconds = max(1, int(timeout_ms)) / 1000.0
    reader = GameStateReader(
        capture=GameWindowCapture(),
        recognizer=EasyOCRRecognizer(),
        teaching_path=Path(__file__).resolve().parents[3] / "mcp" / "config" / "mu_game_window.json",
        scale=1.0,
        grayscale=True,
        threshold=80,
    )
    target = GameTarget(target_id=f"mcp:{hwnd}", hwnd=hwnd, process_name="", window_title="")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0.1:
            break
        observed_text = reader.verify_dynamic_text(target, event_type, timeout_seconds=remaining)
        if observed_text:
            return {
                "success": True,
                "timed_out": False,
                "event_type": event_type,
                **reader.last_dialog_verification,
                ("matched_label" if reader.last_dialog_verification.get("method") == "template_matching"
                 else "observed_text"): observed_text,
            }
        if reader.last_error:
            return {
                "success": False,
                "timed_out": False,
                "event_type": event_type,
                "error": reader.last_error,
                **reader.last_dialog_verification,
            }
        time.sleep(min(0.05, remaining))
    return {
        "success": False,
        "timed_out": True,
        "event_type": event_type,
        "error": f"dialog title was not found within {timeout_ms} ms",
        **reader.last_dialog_verification,
    }


def _keyboard_result(
    *,
    action: AutoAction,
    target: dict[str, Any],
    action_success: bool,
    delivery: str | None = None,
    logs: list[str] | None = None,
    verify_event_type: str = "",
    verify_timeout_ms: int = DEFAULT_DIALOG_VERIFY_TIMEOUT_MS,
) -> dict[str, Any]:
    """Combine an action result with an optional in-tool dialog verification."""
    result: dict[str, Any] = {
        "ok": action_success,
        "action_ok": action_success,
        "target": target,
        "action": _action_to_json(action),
        "logs": logs or [],
    }
    if delivery:
        result["delivery"] = delivery
    if not action_success or not verify_event_type:
        return result

    verification = _await_dynamic_text(int(target["hwnd"]), verify_event_type, verify_timeout_ms)
    result["verification"] = verification
    result["ok"] = bool(verification["success"])
    return result


def _run_keyboard_action(
    value: str,
    text_input_enabled: bool = False,
    delay_seconds: float = 0.0,
    target_window_title: str = "",
    verify_event_type: str = "",
    verify_timeout_ms: int = DEFAULT_DIALOG_VERIFY_TIMEOUT_MS,
) -> dict[str, Any]:
    """Execute an internal Keyboard action and optionally verify a dialog in this same call.

    ``verify_event_type`` names an entry in teaching ``dialogs``. Its title
    check runs only after the key action succeeds and has a ten-second default.
    """
    action, errors = _build_keyboard_action(
        name="MCP Keyboard Action",
        value=value,
        text_input_enabled=text_input_enabled,
        purpose="Executed through MCP",
        delay_seconds=delay_seconds,
        goto_step_enabled=False,
        goto_step_index=0,
    )
    if errors:
        return {"ok": False, "errors": errors}
    try:
        clean_verify_timeout_ms = max(1, int(verify_timeout_ms))
    except (TypeError, ValueError):
        return {"ok": False, "errors": ["verify_timeout_ms must be an integer"]}

    windows, selection_error = _selected_visible_windows()
    if selection_error:
        return {"ok": False, "errors": [selection_error]}

    title_query = str(target_window_title or "").strip()
    if title_query:
        exact = [window for window in windows if str(window.get("title", "")).casefold() == title_query.casefold()]
        matches = exact or [
            window for window in windows
            if title_query.casefold() in str(window.get("title", "")).casefold()
        ]
    else:
        matches = windows

    if not matches:
        return {"ok": False, "errors": [f"Process đã chọn không có cửa sổ: {title_query}"]}
    if len(matches) > 1:
        return {
            "ok": False,
            "errors": ["Process có nhiều cửa sổ; hãy truyền target_window_title đầy đủ"],
            "matches": matches,
        }

    target = matches[0]
    if not text_input_enabled and _post_single_key(int(target["hwnd"]), str(action.value)):
        return _keyboard_result(
            action=action,
            target=target,
            action_success=True,
            delivery="window_message",
            logs=["Queued key message for the selected window without focusing it."],
            verify_event_type=str(verify_event_type or "").strip(),
            verify_timeout_ms=clean_verify_timeout_ms,
        )

    logs: list[str] = []
    captured_stdout = io.StringIO()
    with contextlib.redirect_stdout(captured_stdout):
        from src.logic.system_executor import SystemExecutor

        executor = SystemExecutor(target_window_hwnd=int(target["hwnd"]), ui_log_func=logs.append)
        success = bool(executor.execute(action))
    if success and action.delay > 0:
        time.sleep(action.delay)
    engine_output = [line for line in captured_stdout.getvalue().splitlines() if line.strip()]
    return _keyboard_result(
        action=action,
        target=target,
        action_success=success,
        logs=(logs + engine_output)[-20:],
        verify_event_type=str(verify_event_type or "").strip(),
        verify_timeout_ms=clean_verify_timeout_ms,
    )


@mcp.tool()
def get_daily_events_dialog_info() -> dict[str, Any]:
    """Read remaining Boss, jewel mining, Blood Castle, Devil and IG entries on the selected window.

    Use the already-open Daily Events dialog, or send its configured S key and
    verify the title image. OCR five title-relative teaching regions and return
    integer counts in remaining (boss, jewel, bc, devil, ig) plus OCR evidence.
    Missing or uncertain counts are null and success=false; zero is a valid count.
    Clicks the taught X button after reading, including OCR failures, and verifies
    closure. If closing fails, returns failure with the counters already read.
    Does not enter any event or click any purchase button.
    """
    return _run_companion_tool(read_daily_events, send_key=_post_single_key)


@mcp.tool()
def switch_to_companion_character() -> dict[str, Any]:
    """Switch to the companion currently shown by Companion Management slot 1.

    The selected Gemini Chat window is used directly. This call opens the
    dialog, matches its title and Enter Character button, sends background
    clicks to that HWND, and verifies the window title changed.
    """
    return _run_companion_tool(run_companion_switch)


def _run_companion_tool(action: Callable[..., dict[str, Any]], **arguments: Any) -> dict[str, Any]:
    """Keep game actions on the selected window and keep library output off MCP stdout."""
    captured_stdout = io.StringIO()
    wake_up: dict[str, Any] | None = None
    try:
        with contextlib.redirect_stdout(captured_stdout):
            windows, error = _selected_visible_windows()
            if error:
                return {"success": False, "selection_required": True, "error": error}
            if len(windows) != 1:
                return {
                    "success": False, "selection_required": True,
                    "error": "Select exactly one game window in Gemini Chat",
                }
            wake_up = _wake_selected_window(windows[0])
            result = action(windows[0], **arguments)
    except Exception as error:
        result = {
            "success": False,
            "error": str(error),
            "debug": {
                "stage": "run_selected_window_tool",
                "action": getattr(action, "__name__", str(action)),
                "exception_type": type(error).__name__,
                "traceback": traceback.format_exc(limit=5),
            },
        }
    if wake_up is not None:
        result["wake_up"] = wake_up
    result.setdefault("selection_required", False)
    if result.get("success") is False:
        debug = result.setdefault("debug", {})
        debug.setdefault("action", getattr(action, "__name__", str(action)))
        debug.setdefault("target", result.get("target") or (windows[0] if 'windows' in locals() and len(windows) == 1 else None))
    logs = captured_stdout.getvalue().splitlines()
    if logs:
        result["logs"] = logs[-20:]
    return result


@mcp.tool()
def open_companion_management_dialog() -> dict[str, Any]:
    """Open and image-verify slot 1 Manage Sub-Characters, then close it with the taught X.

    Requires a summoned companion. Reads the button ROI, title image, and title
    threshold from teaching JSON. Does not enter the character. Returns failure
    if the title disappears cannot be verified after the close click.
    """
    return _run_companion_tool(run_open_companion_dialog)


@mcp.tool()
def get_current_character_map() -> dict[str, Any]:
    """Read the selected active character's current map and coordinates from the HUD.

    This is read-only. It returns map, position, coordinates, and is_varka only
    when OCR validates the taught mainInfo.map and mainInfo.position regions.
    It does not open a dialog or change character.
    """
    return _run_companion_tool(read_current_character_map)


@mcp.tool()
def set_main_character_auto_z(running: bool) -> dict[str, Any]:
    """Ensure the selected main character's Auto Z is running or stopped.

    `running=true` starts Auto Z and `running=false` stops it. The tool matches
    the taught triangle/pause icons before and after clicking, and fails when
    the icon does not reach the requested state.
    """
    return _run_companion_tool(set_auto_z_state, running=bool(running))


@mcp.tool()
def start_autoplay_management() -> dict[str, Any]:
    """Start Autoplay Management for the selected main character.

    If it is already running, the tool first stops it. It then verifies the
    Autoplay Management title and Save and Start button before clicking that
    button, and verifies the running icon afterwards.
    """
    return _run_companion_tool(run_start_autoplay_management)


@mcp.tool()
def get_companion_training_state() -> dict[str, Any]:
    """Read whether the selected character's slot-1 companion is training.

    A right-pointing triangle means `training`; two vertical bars mean
    `not_training`. This tool only captures and matches the taught icon.
    """
    return _run_companion_tool(read_companion_training_state)


@mcp.tool()
def get_companion_summoned_state() -> dict[str, Any]:
    """Read slot 1 companion name, server, map, level, reset, and status on the selected window.

    Click the companion slot when present and Manage Sub-Characters is not already
    open. Verify its title image, then OCR the six teaching regions. Click the
    taught X button and verify the dialog closed, including on OCR failure.
    Closing failure preserves the read fields and returns failure. A verified empty slot
    returns companion_summoned=false and character=null. An occluded or uncertain slot
    returns companion_summoned=null and sends no click. Incomplete OCR returns failure
    with partial fields. The historical tool name is retained for existing callers.
    """
    return _run_companion_tool(get_companion_information)


@mcp.tool()
def summon_companion_character(target_character: str) -> dict[str, Any]:
    """Summon the named companion into slot 1 of the selected game window.

    target_character is the companion to summon, not the current window's character.
    Requires the not-summoned icon, verifies Character List by its title image,
    OCRs the configured name list, clicks the unique matching name, and confirms
    the slot icon changed. Uses teaching JSON and background clicks. Closes the
    dialog if OCR finds no unique target. Does not change to the summoned character.
    """
    if not target_character.strip():
        return {"success": False, "error": "target_character must be a non-empty character name"}
    return _run_companion_tool(run_companion_summon, target_character=target_character)


def run_keyboard_mcp_server() -> None:
    """Run the keyboard MCP server over stdio."""
    if sys.stdin is None:
        sys.stdin = open(0, "r", encoding="utf-8", errors="replace", closefd=False)
    if sys.stdout is None:
        sys.stdout = open(1, "w", encoding="utf-8", errors="replace", buffering=1, closefd=False)
    if sys.stderr is None:
        sys.stderr = open(Path(os.devnull), "w", encoding="utf-8")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_keyboard_mcp_server()
