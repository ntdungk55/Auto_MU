"""MCP server exposing the existing Keyboard action to AI clients."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import sys
import time
from typing import Any

from mcp.server import MCPServer

from src.ai_control.servers.process import resolve_selected_process
from src.logic.action_type import ActionMode, ActionType, AutoAction


mcp = MCPServer("Auto_MU Keyboard Actions")

MAX_TEXT_LENGTH = 500
MAX_DELAY_SECONDS = 30.0
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


@mcp.tool()
def keyboard_action_schema() -> dict[str, Any]:
    """Return the supported input contract for an Auto_MU Keyboard action."""
    return {
        "action_type": ActionType.KEYBOARD.value,
        "required": ["name", "value"],
        "fields": {
            "name": {"type": "string", "max_length": 120},
            "purpose": {"type": "string", "default": ""},
            "value": {"type": "string", "description": "Một phím hoặc chuỗi văn bản"},
            "text_input_enabled": {"type": "boolean", "default": False},
            "delay_seconds": {"type": "number", "minimum": 0, "maximum": MAX_DELAY_SECONDS},
            "goto_step_enabled": {"type": "boolean", "default": False},
            "goto_step_index": {"type": "integer", "minimum": 0, "default": 0},
        },
        "special_keys": sorted(SPECIAL_KEYS),
    }


@mcp.tool()
def create_keyboard_action(
    name: str,
    value: str,
    text_input_enabled: bool = False,
    purpose: str = "",
    delay_seconds: float = 1.0,
    goto_step_enabled: bool = False,
    goto_step_index: int = 0,
) -> dict[str, Any]:
    """Create and validate a draft Keyboard action; this does not save a Tool."""
    action, errors = _build_keyboard_action(
        name, value, text_input_enabled, purpose, delay_seconds,
        goto_step_enabled, goto_step_index,
    )
    if errors:
        return {"ok": False, "errors": errors}
    return {"ok": True, "action": _action_to_json(action)}


@mcp.tool()
def validate_keyboard_action(action: dict[str, Any]) -> dict[str, Any]:
    """Validate Keyboard action JSON and return a normalized draft."""
    if not isinstance(action, dict):
        return {"ok": False, "errors": ["action phải là JSON object"]}
    action_type = str(action.get("action_type", ActionType.KEYBOARD.value) or "")
    if action_type != ActionType.KEYBOARD.value:
        return {"ok": False, "errors": [f"action_type phải là '{ActionType.KEYBOARD.value}'"]}

    draft, errors = _build_keyboard_action(
        name=action.get("name", ""),
        value=action.get("value", ""),
        text_input_enabled=bool(action.get("text_input_enabled", False)),
        purpose=action.get("purpose", ""),
        delay_seconds=action.get("delay", action.get("delay_seconds", 1.0)),
        goto_step_enabled=bool(action.get("goto_step_enabled", False)),
        goto_step_index=action.get("goto_step_index", 0),
    )
    if errors:
        return {"ok": False, "errors": errors}
    return {"ok": True, "action": _action_to_json(draft)}


def _selected_visible_windows() -> tuple[list[dict[str, Any]], str | None]:
    process, error = resolve_selected_process()
    if error:
        return [], error
    windows = [window for window in (process or {}).get("windows", []) if window.get("visible")]
    if not windows:
        return [], "Process đã chọn không có cửa sổ hiển thị"
    return windows, None


@mcp.tool()
def list_game_windows() -> dict[str, Any]:
    """List visible windows owned by the currently selected game process."""
    windows, error = _selected_visible_windows()
    if error:
        return {"ok": False, "errors": [error], "windows": []}
    return {"ok": True, "windows": windows}


@mcp.tool()
def run_keyboard_action(
    value: str,
    text_input_enabled: bool = False,
    delay_seconds: float = 0.0,
    target_window_title: str = "",
) -> dict[str, Any]:
    """Execute a Keyboard action in a window of the selected game process."""
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
    logs: list[str] = []
    captured_stdout = io.StringIO()
    with contextlib.redirect_stdout(captured_stdout):
        from src.logic.system_executor import SystemExecutor

        executor = SystemExecutor(target_window_hwnd=int(target["hwnd"]), ui_log_func=logs.append)
        success = bool(executor.execute(action))
    if success and action.delay > 0:
        time.sleep(action.delay)
    engine_output = [line for line in captured_stdout.getvalue().splitlines() if line.strip()]
    return {
        "ok": success,
        "target": target,
        "action": _action_to_json(action),
        "logs": (logs + engine_output)[-20:],
    }


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

