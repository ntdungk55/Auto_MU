"""Tests for the example Keyboard MCP server."""

import importlib.util
from pathlib import Path


SERVER_PATH = Path(__file__).resolve().parents[1] / "src" / "ai_control" / "servers" / "keyboard.py"


def _load_server_module():
    spec = importlib.util.spec_from_file_location("auto_mu_keyboard_mcp", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_create_keyboard_action_draft():
    server = _load_server_module()
    result = server.create_keyboard_action(
        name="Press Enter",
        value="ENTER",
        delay_seconds=0.5,
    )

    assert result["ok"] is True
    assert result["action"]["action_type"] == "Ấn Phím"
    assert result["action"]["value"] == "enter"
    assert result["action"]["delay"] == 0.5


def test_create_keyboard_text_action_preserves_text():
    server = _load_server_module()
    result = server.create_keyboard_action(
        name="Type command",
        value="/truytim HuongYeu36",
        text_input_enabled=True,
    )

    assert result["ok"] is True
    assert result["action"]["value"] == "/truytim HuongYeu36"
    assert result["action"]["text_input_enabled"] is True


def test_invalid_keyboard_action_is_rejected():
    server = _load_server_module()
    result = server.create_keyboard_action(name="", value="not-a-real-key")

    assert result["ok"] is False
    assert len(result["errors"]) == 2


def test_run_keyboard_action_rejects_missing_game_window(monkeypatch):
    server = _load_server_module()
    monkeypatch.setattr(server, "resolve_selected_process", lambda: (None, "Chưa chọn process game"))

    result = server.run_keyboard_action(
        value="enter",
    )

    assert result["ok"] is False
    assert "Chưa chọn process" in result["errors"][0]


def test_list_game_windows_only_returns_selected_process_windows(monkeypatch):
    server = _load_server_module()
    monkeypatch.setattr(
        server,
        "resolve_selected_process",
        lambda: (
            {
                "pid": 123,
                "windows": [
                    {"hwnd": 10, "title": "MU", "visible": True},
                    {"hwnd": 11, "title": "Hidden", "visible": False},
                ],
            },
            None,
        ),
    )

    result = server.list_game_windows()

    assert result == {"ok": True, "windows": [{"hwnd": 10, "title": "MU", "visible": True}]}
