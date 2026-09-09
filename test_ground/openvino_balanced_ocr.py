"""Balanced EasyOCR recognizer inference across Intel CPU and iGPU.

The script keeps capture/preprocessing in RAM, skips CRAFT, and runs two
OpenVINO micro-batches concurrently. Window assignment alternates 3/2 and 2/3
between GPU and CPU on consecutive cycles. Press any key to stop after the
current cycle.
"""

from __future__ import annotations

import argparse
import ctypes
import gc
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import easyocr
import numpy as np
import openvino as ov
import torch
from easyocr.recognition import AlignCollate, custom_mean
from PIL import Image


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[1]
MODEL_DIR = SCRIPT_PATH.parent / "models"
DEFAULT_MODEL_PATH = MODEL_DIR / "easyocr_latin_recognizer.xml"
DEFAULT_LOG_PATH = SCRIPT_PATH.parent / "logs" / "openvino_balanced_ocr.jsonl"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_PATH.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PATH.parent))

from benchmark_mu_roi import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    _append_json_line,
    _capture_all_windows,
    _elapsed_ms,
    _find_target_windows,
    _foreground_info,
    _key_pressed,
    _load_config,
    _now_iso,
    _prepare_global_batch,
    _result_value,
    _text_roi_specs,
    _wait_for_next_cycle,
)


MODEL_HEIGHT = 64
MODEL_WIDTH = 256


class _RecognizerWrapper(torch.nn.Module):
    def __init__(self, recognizer: torch.nn.Module):
        super().__init__()
        self.recognizer = recognizer

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        return self.recognizer(image, None)


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


class OpenVINOBalancedRecognizer:
    def __init__(
        self,
        model_path: Path,
        cpu_threads: int,
        rebuild_model: bool = False,
    ) -> None:
        self.model_path = model_path.resolve()
        self.cpu_threads = cpu_threads
        self.reader = easyocr.Reader(
            ["vi", "en"],
            gpu=False,
            detector=False,
            quantize=False,
            verbose=False,
        )
        self.character = self.reader.character
        self.converter = self.reader.converter
        self.ignore_indices = self._build_ignore_indices()
        self.collate = AlignCollate(
            imgH=MODEL_HEIGHT,
            imgW=MODEL_WIDTH,
            keep_ratio_with_pad=True,
        )

        self.core = ov.Core()
        available = set(self.core.available_devices)
        if "CPU" not in available or "GPU" not in available:
            raise RuntimeError(
                f"OpenVINO requires CPU and GPU; available devices: {sorted(available)}"
            )

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        original_working_directory = Path.cwd()
        try:
            # Intel's GPU compiler may emit diagnostic/cache files relative to
            # the process working directory. Keep all generated artifacts in
            # the ignored model directory instead of the repository root.
            os.chdir(self.model_path.parent)
            if rebuild_model or not self.model_path.exists():
                self._convert_and_save_model()

            cache_dir = self.model_path.parent / "compiled_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.core.set_property({"CACHE_DIR": str(cache_dir)})
            model = self.core.read_model(self.model_path)
            self.compiled_models = {
                "CPU": self.core.compile_model(
                    model,
                    "CPU",
                    {
                        "INFERENCE_NUM_THREADS": cpu_threads,
                        "PERFORMANCE_HINT": "LATENCY",
                    },
                ),
                "GPU": self.core.compile_model(
                    model,
                    "GPU",
                    {
                        "PERFORMANCE_HINT": "LATENCY",
                        "NUM_STREAMS": "1",
                    },
                ),
            }
            self.warmup_ms = self._warm_up()
        finally:
            os.chdir(original_working_directory)

        # OpenVINO owns the deployed weights after compilation. Release the
        # original PyTorch recognizer so RAM is not wasted on a duplicate model.
        self.reader.recognizer = None
        gc.collect()

    def _warm_up(self) -> float:
        started = time.perf_counter()

        def warm_device(device: str) -> None:
            compiled = self.compiled_models[device]
            for batch_size in (20, 30):
                dummy = np.zeros(
                    (batch_size, 1, MODEL_HEIGHT, MODEL_WIDTH),
                    dtype=np.float32,
                )
                compiled([dummy])

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(warm_device, device) for device in ("CPU", "GPU")
            ]
            for future in futures:
                future.result()
        return _elapsed_ms(started)

    def _build_ignore_indices(self) -> list[int]:
        ignore_chars = set(self.character) - set(self.reader.lang_char)
        indices: list[int] = []
        for char in ignore_chars:
            try:
                indices.append(self.character.index(char) + 1)
            except ValueError:
                continue
        return indices

    def _convert_and_save_model(self) -> None:
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        wrapper = _RecognizerWrapper(self.reader.recognizer).eval()
        example = torch.zeros((1, 1, MODEL_HEIGHT, MODEL_WIDTH), dtype=torch.float32)
        ov_model = ov.convert_model(wrapper, example_input=example)
        ov_model.reshape(
            {ov_model.input(0): ov.PartialShape([-1, 1, MODEL_HEIGHT, MODEL_WIDTH])}
        )
        ov.save_model(ov_model, self.model_path, compress_to_fp16=True)

    def _prepare_tensor(self, images: list[np.ndarray]) -> np.ndarray:
        pil_images = [Image.fromarray(image, mode="L") for image in images]
        return self.collate(pil_images).numpy()

    def _decode(self, logits: np.ndarray) -> list[tuple[None, str, float]]:
        shifted = logits - np.max(logits, axis=2, keepdims=True)
        probabilities = np.exp(shifted)
        probabilities /= np.sum(probabilities, axis=2, keepdims=True)
        if self.ignore_indices:
            probabilities[:, :, self.ignore_indices] = 0.0
            denominator = np.sum(probabilities, axis=2, keepdims=True)
            probabilities = np.divide(
                probabilities,
                denominator,
                out=np.zeros_like(probabilities),
                where=denominator != 0,
            )

        indices = np.argmax(probabilities, axis=2)
        lengths = np.full(indices.shape[0], indices.shape[1], dtype=np.int32)
        texts = self.converter.decode_greedy(indices.reshape(-1), lengths)
        max_probabilities = np.max(probabilities, axis=2)
        output: list[tuple[None, str, float]] = []
        for text, row_probabilities, row_indices in zip(
            texts,
            max_probabilities,
            indices,
        ):
            non_blank = row_probabilities[row_indices != 0]
            if non_blank.size == 0:
                non_blank = np.array([0.0], dtype=np.float32)
            output.append((None, text, float(custom_mean(non_blank))))
        return output

    def recognize(
        self,
        device: str,
        images: list[np.ndarray],
    ) -> tuple[list[tuple[None, str, float]], float]:
        if not images:
            return [], 0.0
        tensor = self._prepare_tensor(images)
        started = time.perf_counter()
        compiled = self.compiled_models[device]
        logits = compiled([tensor])[compiled.output(0)]
        inference_ms = _elapsed_ms(started)
        return self._decode(np.asarray(logits)), inference_ms


def _assign_devices(
    windows: list[dict[str, Any]],
    cycle_number: int,
) -> dict[int, str]:
    if not windows:
        return {}
    rotated = windows[:]
    shift = (cycle_number - 1) % len(rotated)
    rotated = rotated[shift:] + rotated[:shift]
    if cycle_number % 2 == 1:
        gpu_count = math.ceil(len(rotated) / 2)
    else:
        gpu_count = len(rotated) // 2
    gpu_hwnds = {window["hwnd"] for window in rotated[:gpu_count]}
    return {
        window["hwnd"]: "GPU" if window["hwnd"] in gpu_hwnds else "CPU"
        for window in windows
    }


def _run_device_batch(
    recognizer: OpenVINOBalancedRecognizer,
    device: str,
    indexed_images: list[tuple[int, np.ndarray]],
) -> dict[str, Any]:
    images = [image for _index, image in indexed_images]
    try:
        results, inference_ms = recognizer.recognize(device, images)
        return {
            "device": device,
            "indices": [index for index, _image in indexed_images],
            "results": results,
            "inferenceMs": inference_ms,
            "error": None,
        }
    except Exception as exc:
        return {
            "device": device,
            "indices": [index for index, _image in indexed_images],
            "results": [],
            "inferenceMs": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _run_cycle(
    cycle_number: int,
    config: dict[str, Any],
    roi_specs: list[dict[str, Any]],
    recognizer: OpenVINOBalancedRecognizer,
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
    images, records, window_errors = _prepare_global_batch(
        captures,
        roi_specs,
        scale,
        threshold,
    )

    device_by_hwnd = _assign_devices(windows, cycle_number)
    indexed_by_device: dict[str, list[tuple[int, np.ndarray]]] = {
        "CPU": [],
        "GPU": [],
    }
    for index, (record, image) in enumerate(zip(records, images)):
        indexed_by_device[device_by_hwnd[record["hwnd"]]].append((index, image))

    ocr_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            device: executor.submit(
                _run_device_batch,
                recognizer,
                device,
                indexed,
            )
            for device, indexed in indexed_by_device.items()
            if indexed
        }
        device_batches = {device: future.result() for device, future in futures.items()}

    # GPU failures fall back to CPU after the normal CPU batch has completed.
    gpu_batch = device_batches.get("GPU")
    if gpu_batch and gpu_batch["error"]:
        fallback_items = indexed_by_device["GPU"]
        fallback = _run_device_batch(recognizer, "CPU", fallback_items)
        fallback["fallbackFrom"] = "GPU"
        device_batches["GPU"] = fallback
        for record in records:
            if device_by_hwnd.get(record["hwnd"]) == "GPU":
                device_by_hwnd[record["hwnd"]] = "CPU_FALLBACK"

    ocr_wall_ms = _elapsed_ms(ocr_started)
    results_by_index: dict[int, Any] = {}
    for batch in device_batches.values():
        for index, result in zip(batch["indices"], batch["results"]):
            results_by_index[index] = result

    parts_by_window: dict[int, dict[str, list[tuple[int, Any]]]] = {
        window["hwnd"]: {} for window in windows
    }
    for index, record in enumerate(records):
        result = results_by_index.get(index)
        if result is None:
            continue
        parts = parts_by_window[record["hwnd"]].setdefault(record["key"], [])
        parts.append((record["lineIndex"], result))

    values_by_window: dict[int, dict[str, Any]] = {}
    for window in windows:
        hwnd = window["hwnd"]
        values_by_window[hwnd] = {
            key: _result_value(parts)
            for key, parts in parts_by_window.get(hwnd, {}).items()
        }

    device_window_counts = {
        device: sum(1 for value in device_by_hwnd.values() if value.startswith(device))
        for device in ("CPU", "GPU")
    }
    device_timing = {
        device: batch.get("inferenceMs") for device, batch in device_batches.items()
    }
    device_batch_log = {
        device: {
            "itemCount": len(batch.get("indices", [])),
            "inferenceMs": batch.get("inferenceMs"),
            "error": batch.get("error"),
            **(
                {"fallbackFrom": batch["fallbackFrom"]}
                if batch.get("fallbackFrom")
                else {}
            ),
        }
        for device, batch in device_batches.items()
    }
    window_output: list[dict[str, Any]] = []
    for window in windows:
        hwnd = window["hwnd"]
        device = device_by_hwnd[hwnd]
        timing_key = "CPU" if device == "CPU_FALLBACK" else device
        count = device_window_counts.get(timing_key, 0)
        batch_ms = device_timing.get(timing_key)
        average_ms = round(batch_ms / count, 3) if batch_ms is not None and count else None
        output = {
            "hwnd": hwnd,
            "pid": window["pid"],
            "title": window["title"],
            "ocrDevice": device,
            "ocrDeviceBatchAveragePerWindowMs": average_ms,
            "mainInfo": values_by_window.get(hwnd, {}),
        }
        if hwnd in window_errors:
            output["error"] = window_errors[hwnd]
        window_output.append(output)

    foreground_after = _foreground_info()
    return {
        "schemaVersion": 1,
        "timestamp": _now_iso(),
        "cycle": cycle_number,
        "windowCount": len(windows),
        "batchRoiCount": len({(record["hwnd"], record["key"]) for record in records}),
        "recognitionItemCount": len(images),
        "ocr": {
            "engine": "OpenVINO EasyOCR recognizer",
            "craftDetectorUsed": False,
            "cpuThreads": recognizer.cpu_threads,
            "gpuStreams": 1,
            "startupWarmupMs": recognizer.warmup_ms,
            "assignment": "alternating 3/2 and 2/3 by window",
        },
        "preprocessing": {
            "scale": scale,
            "grayscale": True,
            "threshold": threshold,
            "thresholdType": "THRESH_BINARY",
        },
        "timingMs": {
            "captureAllWindows": capture_ms,
            "ocrWall": ocr_wall_ms,
            "cpuBatch": device_timing.get("CPU"),
            "gpuBatch": device_timing.get("GPU"),
            "cycleTotal": _elapsed_ms(cycle_started),
        },
        "deviceBatches": device_batch_log,
        "focus": {
            "apiUsed": False,
            "before": foreground_before,
            "after": foreground_after,
            "unchanged": foreground_before["hwnd"] == foreground_after["hwnd"],
        },
        "skippedWindows": skipped,
        "windows": window_output,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Balance EasyOCR recognition across OpenVINO CPU and Intel GPU."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--threshold", type=int, default=80)
    parser.add_argument("--cpu-threads", type=int, default=6)
    parser.add_argument("--interval-ms", type=int, default=0)
    parser.add_argument("--rebuild-model", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--cycles",
        type=int,
        default=0,
        help="Stop after this many cycles; zero means run until a key is pressed.",
    )
    parser.add_argument("--elevated-child", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if (
        args.scale < 1
        or not 0 <= args.threshold <= 255
        or args.cpu_threads < 1
        or args.interval_ms < 0
        or args.cycles < 0
    ):
        print("ERROR: invalid scale, threshold, CPU thread count, or interval.")
        return 2

    if not _is_admin():
        print("Administrator access is required; opening a UAC prompt.")
        if not _relaunch_as_admin():
            print("ERROR: could not relaunch as administrator.")
            return 3
        return 0

    init_started = time.perf_counter()
    recognizer = OpenVINOBalancedRecognizer(
        args.model,
        args.cpu_threads,
        rebuild_model=args.rebuild_model,
    )
    print(f"OpenVINO CPU+GPU initialized in {_elapsed_ms(init_started)} ms.")
    print(f"JSONL log: {args.log.resolve()}")
    if not args.once:
        print("Running continuously. Press any key to stop after the current cycle.")

    config = _load_config(args.config.resolve())
    roi_specs = _text_roi_specs(config)
    cycle_number = 0
    cycle_limit = 1 if args.once else args.cycles
    try:
        while True:
            if not args.once and _key_pressed():
                break
            cycle_number += 1
            payload = _run_cycle(
                cycle_number,
                config,
                roi_specs,
                recognizer,
                args.scale,
                args.threshold,
            )
            _append_json_line(args.log.resolve(), payload)
            timing = payload["timingMs"]
            print(
                f"Cycle {cycle_number}: windows={payload['windowCount']}, "
                f"CPU={timing['cpuBatch']} ms, GPU={timing['gpuBatch']} ms, "
                f"OCR wall={timing['ocrWall']} ms, total={timing['cycleTotal']} ms"
            )
            if (
                (cycle_limit and cycle_number >= cycle_limit)
                or _wait_for_next_cycle(args.interval_ms)
            ):
                break
    except KeyboardInterrupt:
        pass

    print(f"Stopped after {cycle_number} completed cycle(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
