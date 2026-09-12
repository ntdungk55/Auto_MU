"""Manually exercise the complete Daily Events information MCP tool flow.

The script discovers one MU window, persists its PID/HWND through the internal selector,
then calls the semantic Keyboard MCP tool. It sends the `S` key only when
Daily Events is not already visible, then reads the five counters and closes the dialog.
Use --direct to call the same implementation in this process without starting MCP.
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
from src.ai_control.servers.process import select_game_process


def _find_window(title_fragment: str) -> dict[str, Any]:
    """Return the uniquely matching visible MU game window."""
    import win32gui
    import win32process

    query = title_fragment.casefold().strip()
    matches: list[dict[str, Any]] = []

    def collect(hwnd: int, _: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if "mu gamethuvn" not in title.casefold() or query not in title.casefold():
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


def _print_daily_result(result: dict[str, Any]) -> int:
    """Print complete evidence plus the five values, preserving unknown versus zero."""
    _print_result("DAILY EVENTS INFORMATION", result)
    remaining = result.get("remaining") or {}
    print("\nRemaining entries:")
    for key, label in (("boss", "Boss"), ("jewel", "Jewel mining"), ("bc", "BC"),
                       ("devil", "Devil"), ("ig", "IG")):
        value = remaining.get(key)
        print(f"  {label}: {value if value is not None else 'UNKNOWN'}")
    closing = result.get("dialog_close")
    if closing is not None:
        print(f"Dialog closed: {closing.get('closed', False)}")
    return 0 if result.get("success") else 1


def run(title_fragment: str, timeout_seconds: float, *, direct: bool = False) -> int:
    """Select the target internally and execute the semantic dialog MCP tool."""
    target = _find_window(title_fragment)
    _print_result("WINDOW", target)

    if direct:
        from src.ai_control.daily_events_info import get_daily_events_dialog_info
        from src.ai_control.servers.keyboard import _post_single_key

        return _print_daily_result(get_daily_events_dialog_info(target, send_key=_post_single_key))

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
        if "get_daily_events_dialog_info" not in tool_names:
            raise RuntimeError("Keyboard MCP không expose tool get_daily_events_dialog_info")

        selection = select_game_process(
            pid=target["pid"], window_title=target["title"], selected_window_hwnd=target["hwnd"],
        )
        _print_result("SELECTED TARGET", selection)
        if not selection.get("ok"):
            return 1

        result = tool_client.call_tool("get_daily_events_dialog_info", {})
        return _print_daily_result(result)
    finally:
        client.stop()


def main() -> int:
    """Parse manual-test arguments and return a process exit status."""
    _configure_console_output()
    parser = argparse.ArgumentParser(description="Test the complete get_daily_events_dialog_info MCP tool flow.")
    parser.add_argument(
        "--title",
        default="NTD3006",
        help="Unique fragment of the target MU window title (default: NTD3006).",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Call the current Daily Events implementation directly without starting MCP.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="MCP call timeout; must exceed the tool's 10-second title-matching deadline (default: 30).",
    )
    arguments = parser.parse_args()
    try:
        return run(arguments.title, max(15.0, arguments.timeout_seconds), direct=arguments.direct)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
