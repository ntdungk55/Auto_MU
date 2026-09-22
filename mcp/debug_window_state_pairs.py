"""Log the same Window State previous/current pairs used by event observers.

This diagnostic script starts the real GameStateService capture loop and only
prints its stored snapshots. It never focuses the game and never sends input.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_control.servers.game_state import GameStateService, GameStateStore
from src.logic.event_observer import HealthState, is_health_below_transition


def _snapshot_payload(snapshot: Any) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    health = snapshot.main_info.get("healthBar", {})
    health_value = health.get("value") if isinstance(health, dict) else None
    health_ocr = health.get("ocr") if isinstance(health, dict) else None
    return {
        "captured_at": snapshot.captured_at,
        "captured_time": datetime.fromtimestamp(snapshot.captured_at).isoformat(timespec="milliseconds"),
        "hwnd": snapshot.hwnd,
        "title": snapshot.target.get("title", ""),
        "map": snapshot.map or None,
        "position": snapshot.position or None,
        "current_hp": health_value.get("current") if isinstance(health_value, dict) else None,
        "health_raw": health_ocr.get("raw_text") if isinstance(health_ocr, dict) else None,
        "health_method": health_ocr.get("method") if isinstance(health_ocr, dict) else None,
        "health_confidence": health_ocr.get("confidence") if isinstance(health_ocr, dict) else None,
    }


def _print_pair(previous: Any, current: Any, error: str | None) -> None:
    previous_data = _snapshot_payload(previous)
    current_data = _snapshot_payload(current)
    previous_hp = previous_data.get("current_hp") if previous_data else None
    current_hp = current_data.get("current_hp") if current_data else None
    transition = None
    if previous_hp is not None and current_hp is not None:
        if is_health_below_transition(
            HealthState(previous_hp),
            HealthState(current_hp),
            100,
        ):
            transition = "HEALTH_BELOW_THRESHOLD"
        elif previous_hp < 100 <= current_hp:
            transition = "HEALTH_RECOVERED"
        elif previous_hp != current_hp:
            transition = "HEALTH_CHANGED"
    timestamp = datetime.now().strftime("%H:%M:%S")
    if error:
        print(f"{timestamp} | ERROR={error}", flush=True)
        return
    if previous_data is None or current_data is None:
        print(f"{timestamp} | previous_hp=None | current_hp=None | transition=None", flush=True)
        return
    print(
        f"{timestamp} | previous_hp={previous_hp} | current_hp={current_hp} "
        f"| transition={transition} | raw={current_data.get('health_raw')!r} "
        f"| confidence={current_data.get('health_confidence')}",
        flush=True,
    )


def _target_by_title(title_query: str) -> dict[str, Any] | None:
    import win32gui

    matches: list[dict[str, Any]] = []

    def callback(hwnd: int, _extra: Any) -> bool:
        title = str(win32gui.GetWindowText(hwnd) or "")
        if win32gui.IsWindowVisible(hwnd) and title_query.casefold() in title.casefold():
            matches.append({"hwnd": int(hwnd), "title": title, "visible": True})
        return True

    win32gui.EnumWindows(callback, None)
    return matches[0] if len(matches) == 1 else None


class _FixedTargetGameStateService(GameStateService):
    def __init__(self, store: GameStateStore, target: dict[str, Any], interval_seconds: float) -> None:
        super().__init__(store, interval_seconds=interval_seconds)
        self._target = target

    def _selected_target(self) -> dict[str, Any] | None:
        return dict(self._target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Log Window State previous/current pairs")
    parser.add_argument("--title", default="", help="Unique substring of the game window title")
    parser.add_argument("--seconds", type=float, default=60.0, help="How long to log")
    parser.add_argument("--interval", type=float, default=0.5, help="Window State capture interval")
    args = parser.parse_args()

    target = _target_by_title(args.title) if args.title else GameStateService._selected_target()
    if target is None:
        raise SystemExit("Không tìm thấy đúng một game window. Hãy truyền --title, ví dụ --title NTD1009")

    print(json.dumps({
        "logger": "window_state_pairs",
        "target": target,
        "capture_interval": max(0.1, args.interval),
        "duration_seconds": max(0.1, args.seconds),
    }, ensure_ascii=False), flush=True)

    store = GameStateStore()
    service = _FixedTargetGameStateService(store, target, args.interval)
    service.start()
    deadline = time.monotonic() + max(0.1, args.seconds)
    try:
        while time.monotonic() < deadline:
            previous, current, error = store.read()
            _print_pair(previous, current, error)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print(json.dumps({"logger": "window_state_pairs", "stopped": "keyboard_interrupt"}), flush=True)
    finally:
        service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
