"""Manually switch one MU window into its displayed companion character."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_control.companion_switcher import (
    get_companion_summoned_state,
    switch_to_companion_character,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character-name", "--game-window-title", dest="character_name", required=True)
    parser.add_argument(
        "--reference-image", type=Path,
        help="Override the configured title and button teaching with crops from this full dialog screenshot.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    parser.add_argument("--verify-timeout-seconds", type=float, default=3.0)
    parser.add_argument(
        "--check-companion-state",
        action="store_true",
        help="Only check whether slot 1 has a summoned companion; never send a game click.",
    )
    return parser.parse_args()


def _find_window(character_name: str) -> dict[str, Any]:
    import win32gui
    import win32process

    query = character_name.casefold().strip()
    matches: list[dict[str, Any]] = []

    def collect(hwnd: int, _: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        title_match = re.search(r"\(\s*golden\s*-\s*([^)]*?)\s*\)", title, flags=re.IGNORECASE)
        if title_match is None or title_match.group(1).casefold().strip() != query:
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        matches.append({"hwnd": int(hwnd), "pid": int(pid), "title": title})

    win32gui.EnumWindows(collect, None)
    if len(matches) != 1:
        raise RuntimeError(f"Need exactly one visible game window for character {character_name!r}: {matches}")
    return matches[0]


def main() -> int:
    """Run the shared non-focus companion-switching flow for one named window."""
    try:
        arguments = _parse_args()
        target = _find_window(arguments.character_name)
        if arguments.check_companion_state:
            result = {
                "success": True,
                "target": target,
                "precondition": get_companion_summoned_state(int(target["hwnd"])),
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        result = switch_to_companion_character(
            target,
            reference_image=arguments.reference_image,
            dialog_timeout_seconds=arguments.timeout_seconds,
            verify_timeout_seconds=arguments.verify_timeout_seconds,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 1
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
