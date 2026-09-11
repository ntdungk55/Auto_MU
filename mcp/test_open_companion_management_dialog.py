"""Manually open and image-verify Companion Management without switching characters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_control.companion_switcher import open_companion_management_dialog



def _configure_console_output() -> None:
    """Use UTF-8 when PowerShell inherits a legacy Windows code page."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            continue


def _find_window(title_fragment: str) -> dict[str, Any]:
    """Return one visible MU game window whose title contains the fragment."""
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
    if len(matches) != 1:
        raise RuntimeError(f"Cần đúng một window có title chứa {title_fragment!r}: {matches}")
    return matches[0]


def run(title_fragment: str, timeout_seconds: float) -> int:
    """Use the same dialog-opening implementation as Keyboard MCP."""
    target = _find_window(title_fragment)
    result = open_companion_management_dialog(target, dialog_timeout_seconds=timeout_seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1



def main() -> int:
    """Parse arguments and return the manual-test result as an exit status."""
    _configure_console_output()
    parser = argparse.ArgumentParser(description="Test opening the first companion-management dialog.")
    parser.add_argument("--title", default="NTD3001", help="Unique target window-title fragment.")
    parser.add_argument("--timeout-seconds", type=float, default=10.0, help="Title image-matching deadline.")
    arguments = parser.parse_args()
    try:
        return run(arguments.title, max(1.0, arguments.timeout_seconds))
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
