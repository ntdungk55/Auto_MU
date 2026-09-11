"""Tests for process selection shared by game-control MCP servers."""

from src.ai_control.servers import process as process_server
from src.ai_control.shared.selected_process_store import SelectedProcessStore
from src.ai_control.scenario_tool_client import ScenarioToolClient
from types import SimpleNamespace
import pytest


def _candidate(pid: int, name: str = "main.exe", creation: int = 100) -> dict:
    return {
        "pid": pid,
        "process_name": name,
        "exe_path": rf"D:\Game\{name}",
        "creation_time_100ns": creation,
        "start_time_utc": "2026-01-01T00:00:00+00:00",
        "alive": True,
        "identity_verified": True,
        "access_limited": False,
        "windows": [{"hwnd": pid + 1000, "title": f"MU {pid}", "visible": True}],
    }


def test_select_process_by_pid_and_read_it_back(tmp_path, monkeypatch):
    store = SelectedProcessStore(tmp_path / "selected_process.json")
    monkeypatch.setattr(process_server, "selected_process_store", store)
    monkeypatch.setattr(process_server, "inspect_process", lambda pid, **_: _candidate(int(pid)))

    selected = process_server.select_game_process(pid=321)
    current = process_server.get_selected_process_info()

    assert selected["ok"] is True
    assert selected["process"]["pid"] == 321
    assert current["ok"] is True
    assert current["process"]["pid"] == 321


def test_name_search_returns_candidates_when_ambiguous(monkeypatch):
    monkeypatch.setattr(
        process_server,
        "list_processes",
        lambda: [_candidate(10, "main.exe"), _candidate(20, "main.exe")],
    )

    result = process_server.select_game_process(process_name="main.exe")

    assert result["ok"] is False
    assert result["selection_required"] is True
    assert [item["pid"] for item in result["candidates"]] == [10, 20]


def test_pid_reuse_marks_saved_selection_stale(tmp_path, monkeypatch):
    store = SelectedProcessStore(tmp_path / "selected_process.json")
    store.save({"pid": 99, "creation_time_100ns": 111, "selected_at_utc": "earlier"})
    monkeypatch.setattr(process_server, "selected_process_store", store)
    monkeypatch.setattr(process_server, "inspect_process", lambda pid, **_: _candidate(int(pid), creation=222))

    result = process_server.get_selected_process_info()

    assert result["ok"] is False
    assert result["stale"] is True
    assert "PID" in result["errors"][0]


def test_selected_process_store_replaces_json_atomically(tmp_path):
    store = SelectedProcessStore(tmp_path / "runtime" / "selected_process.json")

    store.save({"pid": 1})
    store.save({"pid": 2, "process_name": "main.exe"})

    assert store.load() == {"pid": 2, "process_name": "main.exe"}
    assert list(store.path.parent.glob("*.tmp")) == []


def test_chat_synchronizes_target_without_a_process_mcp_tool(tmp_path, monkeypatch):
    store = SelectedProcessStore(tmp_path / "selected_process.json")
    monkeypatch.setattr(process_server, "selected_process_store", store)
    monkeypatch.setattr(process_server, "inspect_process", lambda pid, **_: _candidate(int(pid)))
    client = ScenarioToolClient(mcp_client=object(), scenario_directory=tmp_path)
    client.synchronize_selected_target(SimpleNamespace(target_id="321:1321"))
    assert store.load()["pid"] == 321
    assert store.load()["selected_window_hwnd"] == 1321
    current, error = process_server.resolve_selected_process()
    assert error is None and current["selected_window_hwnd"] == 1321
    with pytest.raises(RuntimeError, match="does not belong"):
        client.synchronize_selected_target(SimpleNamespace(target_id="321:9999"))
    assert store.load()["selected_window_hwnd"] == 1321
