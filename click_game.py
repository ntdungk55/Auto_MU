import os
import sys
import time

import win32con
import win32gui

from src.logic.action_type import ActionMode, ActionType, AutoAction
from src.logic.game_movement_constants import (
    MAP_MOVE_NEGATIVE_X,
    MAP_MOVE_NEGATIVE_Y,
    MAP_MOVE_POSITIVE_X,
    MAP_MOVE_POSITIVE_Y,
    MOVE_CLICK_DOWN,
    MOVE_CLICK_LEFT,
    MOVE_CLICK_RIGHT,
    MOVE_CLICK_UP,
    MOVEMENT_STEP_INTERVAL_MS,
)
from src.logic.system_executor import SystemExecutor
from src.logic.window_detector import WindowDetector


def _parse_path_args(args: list[str]) -> list[tuple[int, int]]:
    if len(args) < 4 or len(args) % 2 != 0:
        raise ValueError("Usage: python click_game.py path <x1> <y1> <x2> <y2> [x3 y3 ...]")
    values = [int(v) for v in args]
    return [(values[i], values[i + 1]) for i in range(0, len(values), 2)]


def _build_path_clicks(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    clicks: list[tuple[int, int]] = []
    for start, end in zip(points, points[1:]):
        sx, sy = start
        ex, ey = end
        dx = ex - sx
        dy = ey - sy

        if dx > 0:
            clicks.extend([MAP_MOVE_POSITIVE_X] * dx)
        elif dx < 0:
            clicks.extend([MAP_MOVE_NEGATIVE_X] * abs(dx))

        if dy > 0:
            clicks.extend([MAP_MOVE_POSITIVE_Y] * dy)
        elif dy < 0:
            clicks.extend([MAP_MOVE_NEGATIVE_Y] * abs(dy))
    return clicks


def _find_emxinhvui_window():
    return next(
        (
            (hwnd, title)
            for hwnd, title in WindowDetector.find_game_windows()
            if "emxinhvui" in (title or "").lower()
        ),
        None,
    )


def _execute_clicks(clicks: list[tuple[int, int]], interval_ms: int) -> tuple[bool, str, int]:
    target = _find_emxinhvui_window()
    if not target:
        print("Không tìm thấy window EmXinhVui")
        return False, "", 0

    hwnd, title = target
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.2)

    executor = SystemExecutor(target_window_hwnd=hwnd, ui_log_func=lambda _msg: None)
    result = True
    for index, (x, y) in enumerate(clicks):
        action = AutoAction(
            name=f"manual_click_{index + 1}",
            purpose="manual move test",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE,
            click_by_coordinate=True,
            coordinate_click_pos=(x, y),
        )
        result = bool(executor.execute(action)) and result
        if index < len(clicks) - 1 and interval_ms > 0:
            time.sleep(interval_ms / 1000.0)

    return result, title, hwnd


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1].lower() == "path":
        try:
            points = _parse_path_args(sys.argv[2:])
        except ValueError as exc:
            print(exc)
            return 2

        os.environ["CLICK_FALLBACK_POSTMESSAGE"] = "1"
        clicks = _build_path_clicks(points)
        result, title, _hwnd = _execute_clicks(clicks, MOVEMENT_STEP_INTERVAL_MS)
        print(f"title={title}")
        print(f"path={points} clicks={len(clicks)} interval_ms={MOVEMENT_STEP_INTERVAL_MS} result={result}")
        return 0 if result else 1

    if len(sys.argv) not in (3, 4, 5):
        print("Usage: python click_game.py <x> <y> [repeat] [interval_ms]")
        print("Usage: python click_game.py path <x1> <y1> <x2> <y2> [x3 y3 ...]")
        return 2

    x = int(sys.argv[1])
    y = int(sys.argv[2])
    repeat = int(sys.argv[3]) if len(sys.argv) >= 4 else 1
    interval_ms = int(sys.argv[4]) if len(sys.argv) >= 5 else MOVEMENT_STEP_INTERVAL_MS
    repeat = max(1, repeat)
    interval_ms = max(0, interval_ms)
    os.environ["CLICK_FALLBACK_POSTMESSAGE"] = "1"

    target = _find_emxinhvui_window()
    if not target:
        print("Không tìm thấy window EmXinhVui")
        return 3

    hwnd, title = target
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.2)

    screen = win32gui.ClientToScreen(hwnd, (x, y))
    executor = SystemExecutor(target_window_hwnd=hwnd, ui_log_func=lambda _msg: None)
    result = True
    for index in range(repeat):
        action = AutoAction(
            name=f"manual_click_{index + 1}",
            purpose="manual move test",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE,
            click_by_coordinate=True,
            coordinate_click_pos=(x, y),
        )
        result = bool(executor.execute(action)) and result
        if index < repeat - 1 and interval_ms > 0:
            time.sleep(interval_ms / 1000.0)

    print(f"title={title}")
    print(
        f"game_click=({x},{y}) screen_click={screen} "
        f"repeat={repeat} interval_ms={interval_ms} result={result}"
    )
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
