"""Continuously capture all MU windows and OCR every text ROI as one batch.

Screenshots and ROI crops stay in memory. Each cycle appends one compact JSON
object to ``test_ground/logs/ocr_benchmark.jsonl``. Press any key in the
PowerShell window to stop after the current OCR cycle finishes.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import msvcrt
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import win32gui
import win32process
from easyocr.easyocr import imgH as EASYOCR_MODEL_HEIGHT
from easyocr.recognition import get_text


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "mcp" / "config" / "mu_game_window.json"
DEFAULT_LOG_PATH = SCRIPT_PATH.parent / "logs" / "ocr_benchmark.jsonl"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logic.system_executor.ocr_engine import EasyOCREngine  # noqa: E402
from src.logic.system_executor.window_capture import WindowCapture  # noqa: E402


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_as_admin() -> bool:
    child_args = [str(SCRIPT_PATH), *sys.argv[1:]]
    if "--elevated-child" not in child_args:
        child_args.append("--elevated-child")
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        subprocess.list2cmdline(child_args),
        str(PROJECT_ROOT),
        1,
    )
    return int(result) > 32


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def _text_roi_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for key, item in config.get("mainInfo", {}).items():
        if str(item.get("recognitionType", "")).lower() != "text":
            continue
        roi = item.get("roi") or {}
        specs.append(
            {
                "key": key,
                "lineCount": max(1, str(item.get("valuePattern", "")).count("\n") + 1),
                "roi": {
                    "x1": int(roi["x1"]),
                    "y1": int(roi["y1"]),
                    "x2": int(roi["x2"]),
                    "y2": int(roi["y2"]),
                },
            }
        )
    return specs


def _window_info(hwnd: int) -> dict[str, Any]:
    title = win32gui.GetWindowText(hwnd) or ""
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    _thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
    return {
        "hwnd": int(hwnd),
        "pid": int(pid),
        "title": title,
        "clientSize": {"width": right - left, "height": bottom - top},
    }


def _foreground_info() -> dict[str, Any]:
    hwnd = int(win32gui.GetForegroundWindow() or 0)
    if not hwnd:
        return {"hwnd": 0, "title": ""}
    try:
        return {"hwnd": hwnd, "title": win32gui.GetWindowText(hwnd) or ""}
    except Exception:
        return {"hwnd": hwnd, "title": ""}


def _find_target_windows(
    title_prefix: str,
    expected_width: int,
    expected_height: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    matching: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def callback(hwnd: int, _extra: object) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd) or ""
        if not title.startswith(title_prefix):
            return True
        info = _window_info(hwnd)
        size = info["clientSize"]
        if size["width"] == expected_width and size["height"] == expected_height:
            matching.append(info)
        else:
            info["error"] = f"Client size must be {expected_width}x{expected_height}"
            skipped.append(info)
        return True

    win32gui.EnumWindows(callback, None)
    matching.sort(key=lambda item: (item["title"].casefold(), item["hwnd"]))
    skipped.sort(key=lambda item: (item["title"].casefold(), item["hwnd"]))
    return matching, skipped


def _capture_window(window: dict[str, Any]) -> dict[str, Any]:
    try:
        capture = WindowCapture(window["hwnd"])
        capture._log_debug = lambda _message: None
        image = capture.capture()
        if image is None:
            return {**window, "image": None, "error": "WindowCapture returned no image"}
        return {**window, "image": image}
    except Exception as exc:
        return {
            **window,
            "image": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _capture_all_windows(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not windows:
        return []
    with ThreadPoolExecutor(max_workers=len(windows)) as executor:
        return list(executor.map(_capture_window, windows))


def _crop_and_preprocess(
    image: np.ndarray,
    roi: dict[str, int],
    scale: int,
    threshold: int,
) -> np.ndarray:
    x1, y1, x2, y2 = roi["x1"], roi["y1"], roi["x2"], roi["y2"]
    height, width = image.shape[:2]
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError(f"ROI outside captured image {width}x{height}: {roi}")
    crop = image[y1:y2, x1:x2]
    if scale > 1:
        crop = cv2.resize(
            crop,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )
    grayscale = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _threshold_used, binary = cv2.threshold(
        grayscale,
        threshold,
        255,
        cv2.THRESH_BINARY,
    )
    return binary


def _prepare_global_batch(
    captures: list[dict[str, Any]],
    roi_specs: list[dict[str, Any]],
    scale: int,
    threshold: int,
) -> tuple[list[np.ndarray], list[dict[str, Any]], dict[int, str]]:
    crops: list[np.ndarray] = []
    records: list[dict[str, Any]] = []
    errors: dict[int, str] = {}

    for window in captures:
        image = window.get("image")
        if image is None:
            if window.get("error"):
                errors[window["hwnd"]] = str(window["error"])
            continue
        for spec in roi_specs:
            line_count = int(spec["lineCount"])
            base_roi = spec["roi"]
            roi_height = base_roi["y2"] - base_roi["y1"]
            for line_index in range(line_count):
                line_roi = dict(base_roi)
                line_roi["y1"] = base_roi["y1"] + round(
                    roi_height * line_index / line_count
                )
                line_roi["y2"] = base_roi["y1"] + round(
                    roi_height * (line_index + 1) / line_count
                )
                try:
                    crop = _crop_and_preprocess(
                        image,
                        line_roi,
                        scale,
                        threshold,
                    )
                except Exception as exc:
                    errors[window["hwnd"]] = f"{type(exc).__name__}: {exc}"
                    continue
                crops.append(crop)
                records.append(
                    {
                        "hwnd": window["hwnd"],
                        "key": spec["key"],
                        "lineIndex": line_index,
                    }
                )

    return crops, records, errors


def _recognize_batch(reader: Any, images: list[np.ndarray]) -> list[Any]:
    if not images:
        return []
    max_ratio = max(image.shape[1] / max(1, image.shape[0]) for image in images)
    model_width = max(
        EASYOCR_MODEL_HEIGHT,
        math.ceil(max_ratio) * EASYOCR_MODEL_HEIGHT,
    )
    image_list = []
    for image in images:
        height, width = image.shape[:2]
        box = [[0, 0], [width, 0], [width, height], [0, height]]
        image_list.append((box, image))

    ignore_char = "".join(set(reader.character) - set(reader.lang_char))
    return get_text(
        reader.character,
        EASYOCR_MODEL_HEIGHT,
        model_width,
        reader.recognizer,
        reader.converter,
        image_list,
        ignore_char=ignore_char,
        decoder="greedy",
        batch_size=len(image_list),
        workers=0,
        device=reader.device,
    )


def _result_value(parts: list[tuple[int, Any]]) -> dict[str, Any]:
    ordered = [result for _index, result in sorted(parts, key=lambda item: item[0])]
    lines = [str(item[1] or "").strip() for item in ordered if item and len(item) > 1]
    confidences = [float(item[2]) for item in ordered if item and len(item) > 2]
    return {
        "value": "\n".join(line for line in lines if line).strip(),
        "confidence": (
            round(sum(confidences) / len(confidences), 6) if confidences else None
        ),
    }


def _append_json_line(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        stream.write("\n")


def _run_cycle(
    cycle_number: int,
    config: dict[str, Any],
    roi_specs: list[dict[str, Any]],
    reader: Any,
    scale: int,
    threshold: int,
) -> dict[str, Any]:
    cycle_started = time.perf_counter()
    foreground_before = _foreground_info()
    client_area = config["client_area"]
    windows, skipped = _find_target_windows(
        str(config["window_title_prefix"]),
        int(client_area["width"]),
        int(client_area["height"]),
    )

    capture_started = time.perf_counter()
    captures = _capture_all_windows(windows)
    capture_ms = _elapsed_ms(capture_started)
    batch_images, batch_records, window_errors = _prepare_global_batch(
        captures,
        roi_specs,
        scale,
        threshold,
    )

    ocr_started = time.perf_counter()
    batch_results = _recognize_batch(reader, batch_images)
    ocr_ms = _elapsed_ms(ocr_started)
    average_window_ms = round(ocr_ms / len(windows), 3) if windows else None

    parts_by_window: dict[int, dict[str, list[tuple[int, Any]]]] = {
        window["hwnd"]: {} for window in windows
    }
    for record, result in zip(batch_records, batch_results):
        key_parts = parts_by_window[record["hwnd"]].setdefault(record["key"], [])
        key_parts.append((record["lineIndex"], result))

    values_by_window: dict[int, dict[str, Any]] = {}
    for window in windows:
        hwnd = window["hwnd"]
        values_by_window[hwnd] = {
            key: _result_value(parts)
            for key, parts in parts_by_window.get(hwnd, {}).items()
        }

    window_output: list[dict[str, Any]] = []
    for window in windows:
        output = {
            "hwnd": window["hwnd"],
            "pid": window["pid"],
            "title": window["title"],
            "ocrAveragePerWindowMs": average_window_ms,
            "mainInfo": values_by_window.get(window["hwnd"], {}),
        }
        if window["hwnd"] in window_errors:
            output["error"] = window_errors[window["hwnd"]]
        window_output.append(output)

    foreground_after = _foreground_info()
    return {
        "schemaVersion": 4,
        "timestamp": _now_iso(),
        "cycle": cycle_number,
        "windowCount": len(windows),
        "textRoiCountPerWindow": len(roi_specs),
        "batchRoiCount": len({(item["hwnd"], item["key"]) for item in batch_records}),
        "recognitionItemCount": len(batch_images),
        "ocr": {
            "engine": "EasyOCR",
            "mode": "recognizerOnlyBatch",
            "craftDetectorUsed": False,
        },
        "preprocessing": {
            "scale": scale,
            "grayscale": True,
            "threshold": threshold,
            "thresholdType": "THRESH_BINARY",
        },
        "timingMs": {
            "captureAllWindows": capture_ms,
            "ocrAllWindows": ocr_ms,
            "ocrAveragePerWindow": average_window_ms,
            "cycleTotal": _elapsed_ms(cycle_started),
        },
        "focus": {
            "apiUsed": False,
            "before": foreground_before,
            "after": foreground_after,
            "unchanged": foreground_before["hwnd"] == foreground_after["hwnd"],
        },
        "skippedWindows": skipped,
        "windows": window_output,
    }


def _key_pressed() -> bool:
    if not msvcrt.kbhit():
        return False
    msvcrt.getwch()
    return True


def _wait_for_next_cycle(interval_ms: int) -> bool:
    if interval_ms <= 0:
        return _key_pressed()
    deadline = time.perf_counter() + (interval_ms / 1000.0)
    while time.perf_counter() < deadline:
        if _key_pressed():
            return True
        time.sleep(min(0.05, max(0.0, deadline - time.perf_counter())))
    return False


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Continuously batch-OCR every text ROI from all MU windows."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--threshold", type=int, default=80)
    parser.add_argument("--interval-ms", type=int, default=0)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one cycle and exit (intended for automated verification).",
    )
    parser.add_argument("--elevated-child", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.scale < 1 or not 0 <= args.threshold <= 255 or args.interval_ms < 0:
        print(
            "ERROR: --scale must be >= 1, --threshold must be between 0 and 255, "
            "and --interval-ms must be >= 0."
        )
        return 2

    if not _is_admin():
        print("Administrator access is required to capture elevated game windows.")
        print("Opening a UAC prompt; approve it to start in a new console.")
        if not _relaunch_as_admin():
            print("ERROR: could not relaunch as administrator.")
            return 3
        return 0

    config = _load_config(args.config.resolve())
    roi_specs = _text_roi_specs(config)
    engine = EasyOCREngine()
    init_started = time.perf_counter()
    reader = engine._get_reader()
    if reader is None:
        print("ERROR: EasyOCR reader could not be initialized.")
        return 4
    print(f"EasyOCR initialized in {_elapsed_ms(init_started)} ms.")
    print(f"JSONL log: {args.log.resolve()}")
    if not args.once:
        print("Running continuously. Press any key to stop after the current cycle.")

    cycle_number = 0
    try:
        while True:
            if not args.once and _key_pressed():
                break
            cycle_number += 1
            payload = _run_cycle(
                cycle_number,
                config,
                roi_specs,
                reader,
                args.scale,
                args.threshold,
            )
            _append_json_line(args.log.resolve(), payload)
            timing = payload["timingMs"]
            print(
                f"Cycle {cycle_number}: windows={payload['windowCount']}, "
                f"ROIs={payload['batchRoiCount']}, "
                f"OCR all={timing['ocrAllWindows']} ms, "
                f"average/window={timing['ocrAveragePerWindow']} ms, "
                f"total={timing['cycleTotal']} ms"
            )
            if args.once or _wait_for_next_cycle(args.interval_ms):
                break
    except KeyboardInterrupt:
        pass

    print(f"Stopped after {cycle_number} completed cycle(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
