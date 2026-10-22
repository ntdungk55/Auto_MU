"""Run the current companion-info MCP implementation for the selected game window."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_control.servers.keyboard import get_companion_summoned_state


def _write_diagnostic_crops(result: dict[str, Any], directory: Path) -> None:
    """Open the dialog once more and save the exact taught OCR rectangles."""
    import cv2

    from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
    from src.ai_control.companion_switcher import (
        PROJECT_ROOT, TEACHING_PATH, _load_template, _match, open_companion_management_dialog,
    )
    from src.ai_control.dialog_actions import close_taught_dialog
    from src.ai_control.servers.keyboard import _selected_visible_windows, _wake_selected_window

    windows, error = _selected_visible_windows()
    if error or len(windows) != 1:
        raise RuntimeError(error or "Select exactly one game window in Gemini Chat")
    target = windows[0]
    _wake_selected_window(target)
    opened = open_companion_management_dialog(target)
    if not opened.get("success"):
        raise RuntimeError(str(opened.get("error", "Could not open companion dialog")))

    payload = json.loads(TEACHING_PATH.read_text(encoding="utf-8-sig"))
    layout = payload["dialogs"]["dialog.companion_management.opened"]["layout"]
    anchor = layout["Anchor"]
    template = _load_template(PROJECT_ROOT / str(anchor["titleImagePath"]))
    threshold = float(anchor["templateThreshold"])
    hwnd = int(target["hwnd"])
    try:
        image = GameWindowCapture().capture(hwnd)
        if image is None:
            raise RuntimeError("Could not capture the selected game window")
        title = _match(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), template, "Manage Sub-Characters title")
        if float(title["score"]) < threshold:
            raise RuntimeError("Manage Sub-Characters title was not matched for diagnostic capture")
        directory.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(directory / "dialog.png"), image)
        crops: dict[str, Any] = {}
        for field, region in layout["textRegions"].items():
            relative = region["roiRelativeToTitle"]
            roi = {
                axis: int(relative[axis]) + int(title["bbox"][axis[0] + "1"])
                for axis in ("x1", "y1", "x2", "y2")
            }
            crop = image[roi["y1"]:roi["y2"], roi["x1"]:roi["x2"]]
            cv2.imwrite(str(directory / f"{field}.png"), crop)
            cv2.imwrite(str(directory / f"{field}_4x.png"), cv2.resize(crop, None, fx=4, fy=4,
                                                                      interpolation=cv2.INTER_NEAREST))
            crops[field] = roi
        (directory / "regions.json").write_text(
            json.dumps({"title": title, "regions": crops}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result["diagnostic_dir"] = str(directory.resolve())
    finally:
        close_taught_dialog(hwnd, layout, template, threshold, 2.0, "Manage Sub-Characters")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optionally write the JSON result to this file.")
    parser.add_argument("--diagnostic-dir", type=Path, help="Save a full dialog frame and every OCR crop.")
    arguments = parser.parse_args()

    result = get_companion_summoned_state()
    if arguments.diagnostic_dir is not None:
        _write_diagnostic_crops(result, arguments.diagnostic_dir)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(payload + "\n", encoding="utf-8")
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
