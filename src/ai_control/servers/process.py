"""MCP server for selecting and inspecting the target game process."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from typing import Any

try:
    from mcp.server import FastMCP
except ImportError:  # MCP 2.x
    from mcp.server import MCPServer as FastMCP
import win32gui
import win32process

from src.ai_control.shared.selected_process_store import selected_process_store


mcp = FastMCP("Auto_MU Process Selection")

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
_WINDOWS_EPOCH_TICKS = 116444736000000000


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


def _filetime_ticks(value: FILETIME) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _ticks_to_iso(ticks: int | None) -> str | None:
    if not ticks:
        return None
    unix_seconds = (ticks - _WINDOWS_EPOCH_TICKS) / 10_000_000
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).isoformat()


def _windows_for_pid(pid: int) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []

    def callback(hwnd: int, _extra: Any) -> bool:
        try:
            _, owner_pid = win32process.GetWindowThreadProcessId(hwnd)
            if int(owner_pid) != int(pid):
                return True
            title = str(win32gui.GetWindowText(hwnd) or "").strip()
            visible = bool(win32gui.IsWindowVisible(hwnd))
            if title or visible:
                windows.append({"hwnd": int(hwnd), "title": title, "visible": visible})
        except Exception:
            pass
        return True

    win32gui.EnumWindows(callback, None)
    windows.sort(key=lambda item: (not item["visible"], item["title"].casefold(), item["hwnd"]))
    return windows


def _query_process_details(pid: int) -> tuple[str, int | None, bool, str | None]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    open_process.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    query_image = kernel32.QueryFullProcessImageNameW
    query_image.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
    get_times = kernel32.GetProcessTimes
    get_exit_code = kernel32.GetExitCodeProcess

    handle = open_process(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return "", None, True, str(ctypes.WinError(ctypes.get_last_error()))
    try:
        exit_code = wintypes.DWORD()
        alive = bool(get_exit_code(handle, ctypes.byref(exit_code))) and exit_code.value == STILL_ACTIVE

        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        exe_path = buffer.value if query_image(handle, 0, buffer, ctypes.byref(size)) else ""

        creation = FILETIME()
        exit_time = FILETIME()
        kernel_time = FILETIME()
        user_time = FILETIME()
        creation_ticks = None
        if get_times(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel_time), ctypes.byref(user_time)):
            creation_ticks = _filetime_ticks(creation)
        return exe_path, creation_ticks, alive, None
    finally:
        close_handle(handle)


def inspect_process(pid: int, *, known_alive: bool | None = None) -> dict[str, Any]:
    """Return stable identity and top-level windows for one Windows process."""
    try:
        clean_pid = int(pid)
    except (TypeError, ValueError):
        clean_pid = 0
    if clean_pid <= 0:
        return {"pid": clean_pid, "alive": False, "error": "PID không hợp lệ", "windows": []}

    if known_alive is None:
        try:
            known_alive = clean_pid in {int(value) for value in win32process.EnumProcesses()}
        except Exception:
            known_alive = None
    if known_alive is False:
        return {"pid": clean_pid, "alive": False, "error": "Process không còn chạy", "windows": []}

    exe_path, creation_ticks, handle_alive, access_error = _query_process_details(clean_pid)
    alive = bool(known_alive if access_error else handle_alive)
    process_name = Path(exe_path).name if exe_path else ""
    return {
        "pid": clean_pid,
        "process_name": process_name,
        "exe_path": exe_path,
        "creation_time_100ns": creation_ticks,
        "start_time_utc": _ticks_to_iso(creation_ticks),
        "alive": alive,
        "identity_verified": creation_ticks is not None,
        "access_limited": access_error is not None,
        "access_error": access_error,
        "windows": _windows_for_pid(clean_pid) if alive else [],
    }


def list_processes() -> list[dict[str, Any]]:
    try:
        pids = sorted({int(pid) for pid in win32process.EnumProcesses() if int(pid) > 0})
    except Exception:
        return []
    return [inspect_process(pid, known_alive=True) for pid in pids]


def resolve_selected_process() -> tuple[dict[str, Any] | None, str | None]:
    selection = selected_process_store.load()
    if not selection:
        return None, "Chưa chọn process game"
    current = inspect_process(selection.get("pid", 0))
    if not current.get("alive"):
        return current, "Process đã chọn không còn chạy"

    saved_creation = selection.get("creation_time_100ns")
    current_creation = current.get("creation_time_100ns")
    if saved_creation is not None and current_creation is not None and int(saved_creation) != int(current_creation):
        return current, "PID đã được process khác sử dụng lại; hãy chọn lại process"
    current["selected_at_utc"] = selection.get("selected_at_utc")
    current["selected_window_hwnd"] = selection.get("selected_window_hwnd")
    current["selected_window_title"] = selection.get("selected_window_title")
    return current, None


def _matches(candidate: dict[str, Any], process_name: str, window_title: str) -> bool:
    if not candidate.get("alive"):
        return False
    if process_name:
        actual = str(candidate.get("process_name") or "").casefold()
        query = process_name.casefold()
        if query not in actual:
            return False
    if window_title:
        query = window_title.casefold()
        if not any(query in str(window.get("title") or "").casefold() for window in candidate.get("windows", [])):
            return False
    return True


def _public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        key: candidate.get(key)
        for key in (
            "pid", "process_name", "exe_path", "start_time_utc", "alive",
            "identity_verified", "access_limited", "windows",
        )
    }


def select_game_process(
    pid: int = 0,
    process_name: str = "",
    window_title: str = "",
    selected_window_hwnd: int = 0,
) -> dict[str, Any]:
    """Select the process used by all game-control MCP tools.

    Prefer PID when known. Name/title searches return candidates instead of
    selecting arbitrarily when more than one process matches.
    """
    clean_name = str(process_name or "").strip()
    clean_title = str(window_title or "").strip()
    try:
        clean_pid = int(pid)
    except (TypeError, ValueError):
        clean_pid = 0

    if clean_pid > 0:
        candidates = [inspect_process(clean_pid)]
    else:
        if not clean_name and not clean_title:
            return {"ok": False, "errors": ["Cần truyền pid, process_name hoặc window_title"]}
        candidates = list_processes()

    matches = [candidate for candidate in candidates if _matches(candidate, clean_name, clean_title)]
    if not matches:
        return {"ok": False, "errors": ["Không tìm thấy process phù hợp"]}
    if len(matches) > 1:
        return {
            "ok": False,
            "selection_required": True,
            "errors": ["Có nhiều process phù hợp; hãy gọi lại bằng PID"],
            "candidates": [_public_candidate(candidate) for candidate in matches],
        }

    selected = matches[0]
    try:
        selected_hwnd = int(selected_window_hwnd)
    except (TypeError, ValueError):
        selected_hwnd = 0
    selected_window: dict[str, Any] | None = None
    if selected_hwnd > 0:
        selected_window = next(
            (window for window in selected.get("windows", []) if int(window.get("hwnd", 0)) == selected_hwnd),
            None,
        )
        if selected_window is None:
            return {"ok": False, "errors": ["Selected window does not belong to the process"]}
    selection = {
        "version": 2,
        "pid": selected["pid"],
        "process_name": selected.get("process_name", ""),
        "exe_path": selected.get("exe_path", ""),
        "creation_time_100ns": selected.get("creation_time_100ns"),
        "selected_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_window_hwnd": selected_hwnd or None,
        "selected_window_title": (selected_window or {}).get("title", ""),
    }
    selected_process_store.save(selection)
    selected["selected_at_utc"] = selection["selected_at_utc"]
    selected["selected_window_hwnd"] = selection["selected_window_hwnd"]
    selected["selected_window_title"] = selection["selected_window_title"]
    return {"ok": True, "selected": True, "process": _public_candidate(selected)}


def get_selected_process_info() -> dict[str, Any]:
    """Return live information for the process currently used by game tools."""
    process, error = resolve_selected_process()
    if error:
        return {
            "ok": False,
            "selected": selected_process_store.load() is not None,
            "stale": process is not None,
            "errors": [error],
            "process": _public_candidate(process) if process else None,
        }
    return {"ok": True, "selected": True, "stale": False, "process": _public_candidate(process or {})}


def run_process_mcp_server() -> None:
    """Run the process-selection MCP server over stdio."""
    if sys.stdin is None:
        sys.stdin = open(0, "r", encoding="utf-8", errors="replace", closefd=False)
    if sys.stdout is None:
        sys.stdout = open(1, "w", encoding="utf-8", errors="replace", buffering=1, closefd=False)
    if sys.stderr is None:
        sys.stderr = open(Path(os.devnull), "w", encoding="utf-8")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_process_mcp_server()
