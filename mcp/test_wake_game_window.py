"""Test the background center-click wake mechanism on the selected MU window."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_control.companion_switcher import get_companion_summoned_state
from src.ai_control.servers.keyboard import _selected_visible_windows, _wake_selected_window


def _state_summary(hwnd: int) -> dict:
    state = get_companion_summoned_state(hwnd)
    samples = state.get("summoned_indicator_samples", [])
    return {
        "companion_state": state.get("companion_state"),
        "brightness": [sample.get("brightness") for sample in samples],
        "indicator_score": [sample.get("score") for sample in samples],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", help="Require this text in the currently selected window title.")
    parser.add_argument("--observation-delay-ms", type=int, default=500)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    windows, error = _selected_visible_windows()
    if error or len(windows) != 1:
        raise RuntimeError(error or "Select exactly one game window in Gemini Chat")
    target = windows[0]
    if arguments.title and arguments.title.casefold() not in str(target.get("title", "")).casefold():
        raise RuntimeError(f"Selected window is not {arguments.title!r}: {target.get('title')!r}")

    hwnd = int(target["hwnd"])
    before = _state_summary(hwnd)
    wake = _wake_selected_window(target)
    time.sleep(max(0, arguments.observation_delay_ms) / 1000.0)
    after = _state_summary(hwnd)
    result = {
        "success": True,
        "target": target,
        "wake_up": wake,
        "observation_delay_ms": max(0, arguments.observation_delay_ms),
        "before": before,
        "after": after,
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
