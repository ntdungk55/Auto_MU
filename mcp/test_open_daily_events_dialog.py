"""Manually exercise the complete Daily Events MCP tool flow.

The script discovers one MU window, selects its PID/HWND through Process MCP,
then calls the semantic Keyboard MCP tool. It intentionally sends the `S` key
to the selected game window.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_control.mcp_client_manager import MCPClientManager
from src.ai_control.scenario_tool_client import ScenarioToolClient


def _find_window(title_fragment: str) -> dict[str, Any]:
    """Return the first visible top-level window whose title contains the fragment."""
    import win32gui
    import win32process

    query = title_fragment.casefold().strip()
    matches: list[dict[str, Any]] = []

    def collect(hwnd: int, _: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if query not in title.casefold():
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        matches.append({"hwnd": int(hwnd), "pid": int(pid), "title": title})

    win32gui.EnumWindows(collect, None)
    if not matches:
        raise RuntimeError(f"Không tìm thấy window hiển thị có title chứa: {title_fragment!r}")
    if len(matches) > 1:
        formatted = json.dumps(matches, ensure_ascii=False, indent=2)
        raise RuntimeError(f"Có nhiều window khớp; hãy truyền --title cụ thể hơn:\n{formatted}")
    return matches[0]


def _print_result(label: str, payload: Any) -> None:
    """Print one inspectable JSON result without changing MCP stdout."""
    print(f"\n=== {label} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _configure_console_output() -> None:
    """Use UTF-8 when PowerShell inherits a legacy Windows code page."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            continue


def run(title_fragment: str, timeout_seconds: float) -> int:
    """Select the target in Process MCP and execute the semantic dialog tool."""
    target = _find_window(title_fragment)
    _print_result("WINDOW", target)

    client = MCPClientManager(startup_timeout_seconds=20.0, tool_timeout_seconds=timeout_seconds)
    tool_client = ScenarioToolClient(
        mcp_client=client,
        scenario_directory=PROJECT_ROOT / "scenario_engine" / "scenarios",
    )
    client.start()
    try:
        if not client.wait_until_connected(20.0):
            raise RuntimeError(client.status_snapshot().message)

        tools = client.refresh_tools(10.0)
        tool_names = {str(tool["name"]) for tool in tools}
        if "open_daily_events_dialog" not in tool_names:
            raise RuntimeError("Keyboard MCP không expose tool open_daily_events_dialog")

        selection = tool_client.call_tool(
            "select_game_process",
            {
                "pid": target["pid"],
                "window_title": target["title"],
                "selected_window_hwnd": target["hwnd"],
            },
        )
        _print_result("PROCESS MCP SELECTION", selection)
        if not selection.get("ok"):
            return 1

        result = tool_client.call_tool("open_daily_events_dialog", {})
        _print_result("OPEN DAILY EVENTS DIALOG", result)
        return 0 if result.get("ok") else 1
    finally:
        client.stop()


def main() -> int:
    """Parse manual-test arguments and return a process exit status."""
    _configure_console_output()
    parser = argparse.ArgumentParser(description="Test the complete open_daily_events_dialog MCP tool flow.")
    parser.add_argument(
        "--title",
        default="NTD0103",
        help="Unique fragment of the target MU window title (default: NTD0103).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="MCP call timeout; must exceed the tool's 10-second OCR deadline (default: 30).",
    )
    arguments = parser.parse_args()
    try:
        return run(arguments.title, max(15.0, arguments.timeout_seconds))
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
