"""Manually summon one companion or teach the Character List title."""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control.companion_switcher import _open_button_center, get_companion_summoned_state
from src.ai_control.companion_summoner import (
    _read_character_list, _title_anchor_config, _title_search_roi, _title_template_path,
    summon_companion_character,
)
from src.logic.system_executor.mouse_controller import MouseController
from src.logic.system_executor.ocr_engine import EasyOCREngine



def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-character", required=True, help="Current character in the MU title, for example NTD3005.")
    parser.add_argument("--target-character", help="Character to summon, for example NTD3001.")
    parser.add_argument("--teach-title-template", action="store_true", help="Create the Character List title template after the dialog opens.")
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    parser.add_argument("--verify-timeout-seconds", type=float, default=10.0)
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
        match = re.search(r"\(\s*golden\s*-\s*([^)]*?)\s*\)", title, flags=re.IGNORECASE)
        if match is None or match.group(1).casefold().strip() != query:
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        matches.append({"hwnd": int(hwnd), "pid": int(pid), "title": title})

    win32gui.EnumWindows(collect, None)
    if len(matches) != 1:
        raise RuntimeError(f"Need exactly one visible MU window for {character_name!r}: {matches}")
    return matches[0]


def _teach_title_template(image: Any) -> dict[str, Any] | None:
    x1, y1, x2, y2 = _title_search_roi()
    roi = image[y1:y2, x1:x2]
    reader = EasyOCREngine()._get_reader()
    if reader is None:
        raise RuntimeError("EasyOCR reader is unavailable")
    best: tuple[float, Any, str] | None = None
    expected_title = str(_title_anchor_config()["text"]).casefold()
    for bbox, text, _confidence in reader.readtext(roi, detail=1, decoder="greedy"):
        score = SequenceMatcher(None, expected_title, str(text).casefold().strip()).ratio()
        if best is None or score > best[0]:
            best = (score, bbox, str(text))
    if best is None or best[0] < 0.75:
        return None
    _, bbox, observed_text = best
    points = [(int(point[0]) + x1, int(point[1]) + y1) for point in bbox]
    left = max(0, min(point[0] for point in points) - 2)
    top = max(0, min(point[1] for point in points) - 2)
    right = min(image.shape[1], max(point[0] for point in points) + 3)
    bottom = min(image.shape[0], max(point[1] for point in points) + 3)
    title_template_path = _title_template_path()
    title_template_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(title_template_path), image[top:bottom, left:right]):
        raise RuntimeError(f"Could not save title template: {title_template_path}")
    return {"observed_text": observed_text, "bbox": {"x1": left, "y1": top, "x2": right, "y2": bottom}}


def run(arguments: argparse.Namespace) -> int:
    """Use the shared summon flow, retaining opt-in manual title teaching."""
    if not arguments.teach_title_template and not arguments.target_character:
        raise RuntimeError("--target-character is required unless --teach-title-template is used")
    target = _find_window(arguments.game_character)
    if not arguments.teach_title_template:
        result = summon_companion_character(
            target, arguments.target_character,
            dialog_timeout_seconds=arguments.timeout_seconds,
            verify_timeout_seconds=arguments.verify_timeout_seconds,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 1
    hwnd = int(target["hwnd"])
    state = get_companion_summoned_state(hwnd)
    if state["companion_summoned"]:
        raise RuntimeError("Companion is already summoned")
    x, y = _open_button_center()
    MouseController(target_window_hwnd=hwnd).click_at_client(x, y)
    capture = GameWindowCapture()
    deadline = time.monotonic() + max(0.1, float(arguments.timeout_seconds))
    while time.monotonic() < deadline:
        image = capture.capture(hwnd)
        if image is not None:
            taught = _teach_title_template(image)
            if taught is not None:
                character_list = _read_character_list(image, taught["bbox"])
                print(json.dumps({"success": True, "target": target, "precondition": state,
                                  "title_template": taught, "character_list": character_list}, ensure_ascii=False, indent=2))
                return 0
        time.sleep(0.05)
    raise RuntimeError("Character List title was not detected")



def main() -> int:
    try:
        return run(_parse_args())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
