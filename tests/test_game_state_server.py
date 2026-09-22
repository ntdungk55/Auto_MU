"""Tests for the read-only Game State MCP server boundary."""

from src.ai_control.servers import game_state


def test_state_store_returns_latest_complete_snapshot() -> None:
    store = game_state.GameStateStore()
    snapshot = game_state.GameStateSnapshot(
        hwnd=10,
        map="Lorencia",
        position={"x": 12, "y": 34},
        captured_at=123.0,
        target={"hwnd": 10, "title": "MU"},
    )

    store.replace(snapshot)

    previous, actual, error = store.read()
    assert previous is None
    assert actual == snapshot
    assert error is None


def test_state_store_keeps_previous_state_for_comparison() -> None:
    store = game_state.GameStateStore()
    first = game_state.GameStateSnapshot(10, "Lorencia", {"x": 1, "y": 2}, 1.0, {"hwnd": 10})
    second = game_state.GameStateSnapshot(10, "Noria", {"x": 3, "y": 4}, 2.0, {"hwnd": 10})

    store.replace(first)
    store.replace(second)

    previous, current, error = store.read()
    assert previous == first
    assert current == second
    assert error is None


def test_mcp_state_tool_reads_store_without_capture_or_wake(monkeypatch) -> None:
    snapshot = game_state.GameStateSnapshot(
        hwnd=10,
        map="Noria",
        position={"x": 5, "y": 6},
        captured_at=123.0,
        target={"hwnd": 10},
    )
    monkeypatch.setattr(game_state, "_store", store := game_state.GameStateStore())
    store.replace(snapshot)

    result = game_state.get_selected_game_state(include_previous=True)

    assert result["success"] is True
    assert result["map"] == "Noria"
    assert result["position"] == {"x": 5, "y": 6}
    assert result["state"]["hwnd"] == 10
    assert result["previous_state"] is None


def test_mcp_state_tool_reports_incomplete_state(monkeypatch) -> None:
    monkeypatch.setattr(game_state, "_store", store := game_state.GameStateStore())
    store.clear("OCR incomplete")

    result = game_state.get_selected_game_state()

    assert result == {"success": False, "state": None, "error": "OCR incomplete"}


def test_temporary_read_error_keeps_previous_and_current_state() -> None:
    store = game_state.GameStateStore()
    snapshot = game_state.GameStateSnapshot(10, "Lorencia", {"x": 1, "y": 2}, 1.0, {"hwnd": 10})
    store.replace(snapshot)
    store.set_error("temporary OCR failure")

    previous, current, error = store.read()
    assert previous is None
    assert current == snapshot
    assert error == "temporary OCR failure"


def test_state_server_exposes_hud_read_tools() -> None:
    import asyncio

    names = {tool.name for tool in asyncio.run(game_state.mcp.list_tools())}
    assert {"get_selected_game_state", "get_current_character_map", "get_companion_training_state"} <= names
