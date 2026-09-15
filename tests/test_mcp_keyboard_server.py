"""Verify the restricted game MCP catalog and internal target validation."""

import asyncio

import win32con
import win32gui

from src.ai_control.servers import keyboard, process
from src.ai_control.server_registry import default_server_specs

GAME_TOOLS = {
    "get_daily_events_dialog_info", "open_companion_management_dialog",
    "get_current_character_map", "get_companion_summoned_state", "switch_to_companion_character",
    "summon_companion_character", "set_main_character_auto_z", "start_autoplay_management",
    "get_companion_training_state",
}


def test_only_game_tools_are_exposed() -> None:
    assert {tool.name for tool in asyncio.run(keyboard.mcp.list_tools())} == GAME_TOOLS
    assert asyncio.run(process.mcp.list_tools()) == []
    assert [spec.name for spec in default_server_specs()] == ["keyboard"]


def test_daily_events_rejects_missing_game_window(monkeypatch) -> None:
    monkeypatch.setattr(keyboard, "resolve_selected_process", lambda: (None, "No selected game process"))
    result = keyboard.get_daily_events_dialog_info()
    assert result["success"] is False
    assert result["selection_required"] is True
    assert "No selected game process" in result["error"]


def test_internal_window_selection_filters_hidden_windows(monkeypatch) -> None:
    monkeypatch.setattr(keyboard, "resolve_selected_process", lambda: (
        {"pid": 123, "windows": [
            {"hwnd": 10, "title": "MU", "visible": True},
            {"hwnd": 11, "title": "Hidden", "visible": False},
        ]}, None,
    ))
    windows, error = keyboard._selected_visible_windows()
    assert error is None
    assert windows == [{"hwnd": 10, "title": "MU", "visible": True}]


def test_wake_clicks_client_top_left_without_changing_foreground(monkeypatch) -> None:
    messages = []
    monkeypatch.setattr(win32gui, "IsWindow", lambda hwnd: hwnd == 10)
    monkeypatch.setattr(win32gui, "IsWindowVisible", lambda hwnd: hwnd == 10)
    monkeypatch.setattr(win32gui, "GetClientRect", lambda hwnd: (0, 0, 800, 600))
    monkeypatch.setattr(win32gui, "GetForegroundWindow", lambda: 99)
    monkeypatch.setattr(win32gui, "PostMessage", lambda hwnd, message, wparam, lparam: messages.append(
        (hwnd, message, wparam, lparam)
    ))

    result = keyboard._wake_selected_window({"hwnd": 10})

    expected_lparam = (1 << 16) | 1
    assert messages == [
        (10, win32con.WM_MOUSEMOVE, 0, expected_lparam),
        (10, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, expected_lparam),
        (10, win32con.WM_LBUTTONUP, 0, expected_lparam),
    ]
    assert result["method"] == "background_top_left_click"
    assert (result["x"], result["y"]) == (1, 1)
    assert result["focus_requested"] is False
    assert result["foreground_changed"] is False
    assert result["delay_ms"] == 0
