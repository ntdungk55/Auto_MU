"""Screen Scan Service - Singleton background service for periodic screen OCR."""

import threading
import time
from typing import Callable, Optional

import cv2
import numpy as np

from .ocr_engine import OCRFactory
from .ocr_preprocessor import OCRPreprocessor
from .window_capture import WindowCapture


class OCRSubscription:
    """Represents a single OCR subscription from an action."""

    def __init__(
        self,
        action_id: str,
        hwnd: int,
        roi: Optional[tuple],
        ocr_engine: str,
        ocr_algorithms: list,
        callback: Callable[[str], None],
        pair_group_id: Optional[str] = None,
        pair_role: Optional[str] = None,
        pair_log_callback: Optional[Callable[[str, dict], None]] = None,
    ):
        self.action_id = action_id
        self.hwnd = hwnd
        self.roi = roi
        self.ocr_engine = ocr_engine
        self.ocr_algorithms = ocr_algorithms
        self.callback = callback
        self.pair_group_id = pair_group_id
        self.pair_role = pair_role
        self.pair_log_callback = pair_log_callback


class ScreenScanService:
    """Singleton background service that periodically captures screen and runs OCR."""

    _instance: Optional["ScreenScanService"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "ScreenScanService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ScreenScanService()
        return cls._instance

    def __init__(self, interval_ms: int = 1000):
        self._interval = interval_ms / 1000.0
        self._subscribers: dict[str, OCRSubscription] = {}
        self._sub_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._window_captures: dict[int, WindowCapture] = {}
        self._cycle_counter = 0

    def _log_timing(self, stage: str, started_at: float, **fields) -> None:
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        parts = [f"{key}={value}" for key, value in fields.items()]
        suffix = f" {' '.join(parts)}" if parts else ""
        print(f"[ScreenScanService][Timing] {stage} elapsed_ms={elapsed_ms:.2f}{suffix}")

    @staticmethod
    def _apply_single_algorithm(img: np.ndarray, config: dict) -> np.ndarray:
        if img is None or img.size == 0 or not config:
            return img

        if config.get("binary_threshold"):
            threshold_value = int(config.get("threshold_value", 127))
            threshold_type = int(config.get("threshold_type", 0))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh_type = cv2.THRESH_BINARY if threshold_type == 0 else cv2.THRESH_BINARY_INV
            _, binary = cv2.threshold(gray, threshold_value, 255, thresh_type)
            img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

        if config.get("adaptive_threshold_mean") or config.get("adaptive_threshold_gaussian"):
            adaptive_max_value = max(0, min(int(config.get("adaptive_max_value", 255)), 255))
            adaptive_threshold_type = int(config.get("adaptive_threshold_type", 0))
            adaptive_block_size = max(3, int(config.get("adaptive_block_size", 11)))
            if adaptive_block_size % 2 == 0:
                adaptive_block_size += 1
            adaptive_c = int(config.get("adaptive_c", 2))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh_type = cv2.THRESH_BINARY if adaptive_threshold_type == 0 else cv2.THRESH_BINARY_INV
            adaptive_method = (
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C
                if config.get("adaptive_threshold_gaussian")
                else cv2.ADAPTIVE_THRESH_MEAN_C
            )
            adaptive = cv2.adaptiveThreshold(
                gray,
                adaptive_max_value,
                adaptive_method,
                thresh_type,
                adaptive_block_size,
                adaptive_c,
            )
            img = cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR)

        preprocessor = OCRPreprocessor(img)
        if config.get("upscale"):
            preprocessor.upscale(config["upscale"])
        if config.get("enhance_contrast"):
            preprocessor.enhance_contrast()
        if config.get("sharpen"):
            preprocessor.sharpen(config.get("sharpen_strength", 1.5))
        if config.get("denoise"):
            preprocessor.denoise(config.get("denoise_strength", 9))
        return preprocessor.build()

    def subscribe(self, subscription: OCRSubscription) -> None:
        with self._sub_lock:
            self._subscribers[subscription.action_id] = subscription
            print(
                f"[ScreenScanService] Subscribed action_id={subscription.action_id} "
                f"hwnd={subscription.hwnd} roi={subscription.roi} engine={subscription.ocr_engine}"
            )
        self._ensure_running()

    def unsubscribe(self, action_id: str) -> None:
        with self._sub_lock:
            self._subscribers.pop(action_id, None)
            print(f"[ScreenScanService] Unsubscribed action_id={action_id}")
            if not self._subscribers:
                self._stop_event.set()

    def _ensure_running(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._scan_loop, daemon=True, name="ScreenScanService")
            self._thread.start()

    def _scan_loop(self) -> None:
        print("[ScreenScanService] Scan loop started")
        while not self._stop_event.is_set():
            cycle_started = time.perf_counter()
            self._cycle_counter += 1
            cycle_id = self._cycle_counter

            with self._sub_lock:
                subs = list(self._subscribers.values())

            if not subs:
                break

            hwnd_screenshots: dict[int, Optional[np.ndarray]] = {}
            for sub in subs:
                if sub.hwnd in hwnd_screenshots:
                    continue
                print(f"[ScreenScanService] Capturing hwnd={sub.hwnd} for {len(subs)} subscriber(s) cycle={cycle_id}")
                capture_started = time.perf_counter()
                hwnd_screenshots[sub.hwnd] = self._capture(sub.hwnd)
                self._log_timing("capture_window", capture_started, cycle=cycle_id, hwnd=sub.hwnd)
                if hwnd_screenshots[sub.hwnd] is None:
                    print(f"[ScreenScanService] Capture returned None for hwnd={sub.hwnd}")
                else:
                    shape = getattr(hwnd_screenshots[sub.hwnd], "shape", None)
                    print(f"[ScreenScanService] Capture ok hwnd={sub.hwnd} shape={shape}")

            callback_results: list[tuple[OCRSubscription, str]] = []
            pair_results: dict[str, dict[str, tuple[OCRSubscription, str]]] = {}
            for sub in subs:
                screenshot = hwnd_screenshots.get(sub.hwnd)
                if screenshot is None:
                    continue
                try:
                    crop_started = time.perf_counter()
                    roi_img = self._crop(screenshot, sub.roi)
                    self._log_timing("crop_roi", crop_started, cycle=cycle_id, action_id=sub.action_id, roi=sub.roi)
                    if roi_img is None:
                        print(f"[ScreenScanService] Crop returned None for action_id={sub.action_id} roi={sub.roi}")
                        continue

                    ocr_started = time.perf_counter()
                    text = self._run_ocr(roi_img, sub.ocr_engine, sub.ocr_algorithms)
                    self._log_timing(
                        "ocr_pipeline",
                        ocr_started,
                        cycle=cycle_id,
                        action_id=sub.action_id,
                        engine=sub.ocr_engine,
                        roi_shape=getattr(roi_img, "shape", None),
                    )
                    del roi_img
                    if sub.pair_group_id and sub.pair_role:
                        pair_results.setdefault(sub.pair_group_id, {})[sub.pair_role] = (sub, text)
                    else:
                        callback_results.append((sub, text))
                except Exception as e:
                    print(f"[ScreenScanService] Error processing {sub.action_id}: {e}")

            for sub, text in callback_results:
                try:
                    callback_started = time.perf_counter()
                    sub.callback(text)
                    self._log_timing("callback", callback_started, cycle=cycle_id, action_id=sub.action_id)
                except Exception as e:
                    print(f"[ScreenScanService] Error in callback {sub.action_id}: {e}")

            for group_id, role_map in pair_results.items():
                text_map = {role: item[1] for role, item in role_map.items()}
                log_callback = None
                for sub, _ in role_map.values():
                    if sub.pair_log_callback:
                        log_callback = sub.pair_log_callback
                        break
                if log_callback:
                    try:
                        pair_log_started = time.perf_counter()
                        log_callback(group_id, text_map)
                        self._log_timing("pair_log_callback", pair_log_started, cycle=cycle_id, group_id=group_id)
                    except Exception as e:
                        print(f"[ScreenScanService] Error in pair log callback {group_id}: {e}")

                for role in ("channel", "notify"):
                    if role not in role_map:
                        continue
                    sub, text = role_map[role]
                    try:
                        callback_started = time.perf_counter()
                        sub.callback(text)
                        self._log_timing("pair_callback", callback_started, cycle=cycle_id, action_id=sub.action_id, role=role)
                    except Exception as e:
                        print(f"[ScreenScanService] Error in callback {sub.action_id}: {e}")

            for img in hwnd_screenshots.values():
                del img
            hwnd_screenshots.clear()
            self._log_timing("scan_cycle_total", cycle_started, cycle=cycle_id, subscribers=len(subs))
            self._stop_event.wait(timeout=self._interval)

    def _capture(self, hwnd: int) -> Optional[np.ndarray]:
        try:
            if hwnd not in self._window_captures:
                self._window_captures[hwnd] = WindowCapture(hwnd)
            return self._window_captures[hwnd].capture()
        except Exception as e:
            print(f"[ScreenScanService] Capture failed for hwnd={hwnd}: {e}")
            return None

    def _crop(self, screenshot: np.ndarray, roi: Optional[tuple]) -> Optional[np.ndarray]:
        if roi is None:
            return screenshot
        x, y, w, h = roi
        img_h, img_w = screenshot.shape[:2]
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        x2 = max(x + 1, min(x + w, img_w))
        y2 = max(y + 1, min(y + h, img_h))
        return screenshot[y:y2, x:x2].copy()

    def _run_ocr(self, img: np.ndarray, engine: str, algorithms: list) -> str:
        try:
            original_shape = getattr(img, "shape", None)
            preprocessing_started = time.perf_counter()

            if algorithms:
                for algo in algorithms:
                    config = algo.get("config", {}) if isinstance(algo, dict) else {}
                    img = self._apply_single_algorithm(img, config)

            preprocessing_time = (time.perf_counter() - preprocessing_started) * 1000.0
            engine_sel = str(engine or "auto").lower()
            print(f"[ScreenScanService] Creating OCR engine: {engine_sel}")
            ocr = OCRFactory.create(engine_sel)

            print(f"\n{'='*50}")
            print("🔍 SCREEN SCAN SERVICE OCR RESULTS")
            print(f"{'='*50}")
            print(f"📊 Engine: {engine_sel}")
            print(f"⚙️  Algorithms: {len(algorithms)} preprocessing steps")
            for index, algo in enumerate(algorithms):
                config = algo.get("config", {}) if isinstance(algo, dict) else {}
                algo_name = algo.get("name", "Unknown") if isinstance(algo, dict) else str(algo)
                print(f"    {index + 1}. {algo_name} - {config}")

            print("⏱️  Image Processing:")
            print(f"    🖼️  Original size: {original_shape}")
            print(f"    🖼️  Post-process size: {getattr(img, 'shape', None)}")
            print(f"    ⚙️  Preprocessing time: {preprocessing_time:.2f}ms")
            print(f"    🔧 Total algorithms: {len(algorithms)}")

            ocr_started = time.perf_counter()
            result = ocr.recognize(img) or ""
            ocr_time = (time.perf_counter() - ocr_started) * 1000.0

            print("⏱️  OCR Recognition:")
            print(f"    🤖 Engine time: {ocr_time:.2f}ms")
            print(f"    📏 Total time: {(preprocessing_time + ocr_time):.2f}ms")
            print("📄 OCR Text:")
            print("-" * 30)
            if result.strip():
                print(f"\"{result.strip()}\"")
            else:
                print("(No text detected)")
            print("-" * 30)
            print(f"📏 Text Length: {len(result)} characters")
            print(f"🎯 Words: {len(result.split()) if result.strip() else 0}")
            print(f"{'='*50}\n")
            print(f"[ScreenScanService] OCR completed, engine={engine_sel}, text_len={len(result)}")
            return result
        except Exception as e:
            print(f"[ScreenScanService] OCR failed: {e}")
            return ""
