"""Verify the restricted game MCP catalog and internal target validation."""

import asyncio

from src.ai_control.servers import keyboard, process
from src.ai_control.server_registry import default_server_specs

GAME_TOOLS = {
    "get_daily_events_dialog_info", "open_companion_management_dialog",
    "get_companion_summoned_state", "switch_to_companion_character",
    "summon_companion_character",
}


def test_only_five_game_tools_are_exposed() -> None:
    assert {tool.name for tool in asyncio.run(keyboard.mcp.list_tools())} == GAME_TOOLS
    assert asyncio.run(process.mcp.list_tools()) == []
    assert [spec.name for spec in default_server_specs()] == ["keyboard"]


def test_daily_events_rejects_missing_game_window(monkeypatch) -> None:
    monkeypatch.setattr(keyboard, "resolve_selected_process", lambda: (None, "No selected game process"))
    result = keyboard.get_daily_events_dialog_info()
    assert result["success"] is False
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
