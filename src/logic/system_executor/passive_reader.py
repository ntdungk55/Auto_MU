"""Passive Reader - Passive read loop extracted from SystemExecutor."""

import os
import time
import cv2
import numpy as np
from datetime import datetime
from typing import Callable, Optional


class PassiveReader:
    """Passive read loop: OCR/Gemini on new frames, no clicks."""

    def __init__(
        self,
        ui_log_func: Callable[[str], None],
        capture_fn: Callable[[], Optional[np.ndarray]],
        find_image_fn: Callable,
        ocr_runner,
        gemini_processor,
        telegram_notifier,
        text_filter,
        log_manager,
        passive_cache: dict,
        escape_html_fn: Callable[[str], str],
        engine_ref,
    ):
        """Initialize PassiveReader.

        Args:
            ui_log_func: Function to log UI messages
            capture_fn: Function to capture window screenshot
            find_image_fn: Function to find image in window
            ocr_runner: OCRRunner instance
            gemini_processor: GeminiProcessor instance
            telegram_notifier: TelegramNotifier instance
            text_filter: TextFilter instance
            log_manager: LogManager instance
            passive_cache: Shared passive cache dict
            escape_html_fn: Function to escape HTML
            engine_ref: Reference holder with .engine attribute (for stop checks)
        """
        self._ui_log = ui_log_func
        self._capture = capture_fn
        self._find_image = find_image_fn
        self._ocr_runner = ocr_runner
        self._gemini_processor = gemini_processor
        self._telegram_notifier = telegram_notifier
        self._text_filter = text_filter
        self._log_manager = log_manager
        self._passive_cache = passive_cache
        self._escape_html = escape_html_fn
        self._engine_ref = engine_ref

    def _quick_hash(self, bgr: np.ndarray) -> str:
        """Simple perceptual hash for frame change detection."""
        try:
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        except Exception:
            gray = bgr
        try:
            small = cv2.resize(gray, (32, 32))
        except Exception:
            small = gray
        mean = float(small.mean()) if hasattr(small, "mean") else 0.0
        bits = small > mean
        try:
            return bits.flatten().astype(np.uint8).tobytes().hex()
        except Exception:
            return str(hash(small.tobytes() if hasattr(small, "tobytes") else str(small)))

    def _get_engine(self):
        """Get engine from reference holder."""
        return getattr(self._engine_ref, 'engine', None)

    def run(self, action, timeout: Optional[float] = None):
        """Passive read: only OCR/Gemini on new frames, no clicks/detect.

        Args:
            action: AutoAction with passive read settings
            timeout: Optional timeout (None = run until engine stops)

        Returns:
            False if engine stopped, None if cancelled
        """
        if timeout is None:
            timeout = float(getattr(action, "timeout", 5.0) or 5.0)
        check_interval = float(getattr(action, "check_interval", 1.0) or 1.0)
        sample_every = max(1, int(getattr(action, "passive_sample_every", 1) or 1))
        only_new = bool(getattr(action, "passive_only_new_frame", True))
        keywords_csv = str(getattr(action, "passive_keywords", "") or "")
        keywords = [k.strip().lower() for k in keywords_csv.split(",") if k.strip()]

        self._ui_log(f"<b style='color:blue;'>[Passive Start]</b> Action: {action.name}")
        self._ui_log(f"<b style='color:blue;'>[Passive Config]</b> check_interval={check_interval}s, sample_every={sample_every}, only_new={only_new}")
        self._ui_log(f"<b style='color:green;'>[Passive Mode]</b> Running continuously (no timeout)")
        if keywords:
            self._ui_log(f"<b style='color:blue;'>[Passive Config]</b> Keywords: {keywords}")

        key = f"{getattr(action, 'name', '')}|{getattr(action, 'image_path', '')}"
        cache_entry = self._passive_cache.get(key, {})
        last_hash = cache_entry.get("hash")
        last_ocr_text = cache_entry.get("ocr_text", "")
        last_gemini_result = cache_entry.get("gemini_result", "")

        start = time.time()
        last_capture = start - check_interval
        shot_idx = 0

        self._ui_log(f"<b style='color:green;'>[Passive]</b> Sẽ bắt đầu OCR ngay lần đầu (last_capture được set để chạy ngay)")

        while True:
            engine = self._get_engine()
            if engine and (not engine.is_running or engine.should_stop_completely):
                self._ui_log("<b style='color:red;'>[Passive]</b> Engine stopped, exiting")
                return False
            if engine and bool(getattr(engine, "cancel_cycle_requested", False)):
                self._ui_log("<b style='color:orange;'>[Passive]</b> Cancel requested")
                return None

            now = time.time()
            if now - last_capture < check_interval:
                time.sleep(0.05)
                continue
            last_capture = now
            shot_idx += 1

            self._ui_log(f"<b style='color:gray;'>[Passive]</b> Shot #{shot_idx} (elapsed: {now-start:.1f}s)")

            if shot_idx % sample_every != 0:
                self._ui_log(f"<b style='color:gray;'>[Passive]</b> Skip shot #{shot_idx} (sample_every={sample_every})")
                continue

            self._ui_log("<b style='color:blue;'>[Passive]</b> Capturing screenshot...")
            frame = self._capture()
            if frame is None:
                self._ui_log("<b style='color:red;'>[Passive]</b> Không thể chụp màn hình")
                return False

            roi_frame = self._extract_roi(frame, action)

            current_hash = self._quick_hash(roi_frame)
            self._ui_log(f"<b style='color:gray;'>[Passive]</b> Frame hash: {current_hash[:8]}...")

            if only_new and last_hash and current_hash == last_hash:
                self._ui_log("<b style='color:gray;'>[Passive]</b> Frame giống frame trước, hiển thị kết quả cũ")
                self._show_cached_results(last_ocr_text, last_gemini_result, keywords, keywords_csv, action, key)
                continue

            self._passive_cache[key] = {"hash": current_hash, "time": now}
            last_hash = current_hash

            self._ui_log("<b style='color:blue;'>[Passive]</b> Frame mới, đang OCR...")
            text, engine_used = self._ocr_runner.run(roi_frame, action)
            self._ui_log(f"<b style='color:blue;'>[Passive]</b> OCR engine used: {engine_used}")

            if not text:
                self._ui_log("<b style='color:orange;'>[Passive]</b> OCR rỗng, bỏ qua frame này")
                continue

            self._ui_log(
                f"<b>[Passive OCR]</b> Text length: {len(text)} chars<br>"
                f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(text)}</pre>"
            )

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] [PASSIVE OCR] Engine: {engine_used} | Length: {len(text)} chars")
            print(f"[{timestamp}] [PASSIVE OCR] Data: {text[:200]}..." if len(text) > 200 else f"[{timestamp}] [PASSIVE OCR] Data: {text}")

            gemini_out = self._run_gemini(text, action)

            self._passive_cache[key] = {
                "hash": current_hash,
                "time": now,
                "ocr_text": text,
                "gemini_result": gemini_out or "",
                "last_resolved": cache_entry.get("last_resolved", ""),
            }
            last_ocr_text = text
            last_gemini_result = gemini_out or ""

            if keywords:
                lower_text = text.lower()
                hit = any(k in lower_text for k in keywords)
                matched_keywords = [k for k in keywords if k in lower_text]
                self._ui_log(f"<b>[Passive Keyword]</b> {'CÓ' if hit else 'KHÔNG'} (keywords: {keywords_csv})")
                if matched_keywords:
                    self._ui_log(f"<b style='color:green;'>[Passive Keyword]</b> Matched: {matched_keywords}")

            if bool(getattr(action, "notification_enabled", False)):
                self._send_notification(text, gemini_out, action, engine_used)

            self._ui_log(f"<b style='color:green;'>[Passive Success]</b> Processed frame successfully in {time.time()-start:.1f}s")

            if check_interval > 0:
                self._ui_log(f"<b style='color:gray;'>[Passive]</b> Waiting {check_interval}s before next capture...")
                sleep_end = time.time() + check_interval
                while time.time() < sleep_end:
                    eng = self._get_engine()
                    if eng and (not eng.is_running or eng.should_stop_completely):
                        self._ui_log("<b style='color:orange;'>[Passive]</b> Engine stopped during sleep")
                        return False
                    time.sleep(0.1)

    def run_detect_image(self, action) -> Optional[bool]:
        """Passive detect image: wait for template to appear.

        Args:
            action: AutoAction with detect_image settings

        Returns:
            True: Image found, False: Timeout, None: Cancelled
        """
        timeout = float(getattr(action, "passive_detect_timeout", 30.0) or 30.0)
        threshold = float(getattr(action, "passive_detect_threshold", 0.4) or 0.4)
        check_interval = float(getattr(action, "check_interval", 1.0) or 1.0)

        use_fixed_roi = bool(getattr(action, "use_fixed_roi", False))
        has_image = action.image_path and os.path.exists(action.image_path)

        if not use_fixed_roi and not has_image:
            self._ui_log("<b style='color:red;'>[Passive Detect]</b> Thất bại: chưa cấu hình ảnh template hoặc vùng ROI")
            return False

        self._ui_log(f"<b style='color:blue;'>[Passive Detect]</b> Action: {action.name}")
        self._ui_log(f"<b style='color:blue;'>[Passive Detect]</b> Timeout: {timeout}s, Threshold: {threshold}, Interval: {check_interval}s")
        if has_image:
            self._ui_log(f"<b style='color:blue;'>[Passive Detect]</b> Template: {action.image_path}")

        start_time = time.time()
        best_score = 0.0
        check_count = 0

        while True:
            engine = self._get_engine()
            if engine and (not engine.is_running or engine.should_stop_completely):
                self._ui_log("<b style='color:orange;'>[Passive Detect]</b> Engine stopped, exiting")
                return None
            if engine and bool(getattr(engine, "cancel_cycle_requested", False)):
                self._ui_log("<b style='color:orange;'>[Passive Detect]</b> Cancel requested")
                return None

            elapsed = time.time() - start_time
            if elapsed > timeout:
                self._ui_log(f"<b style='color:red;'>[Passive Detect]</b> Timeout ({elapsed:.1f}s > {timeout}s)")
                self._ui_log(f"<b style='color:red;'>[Passive Detect]</b> Best score: {best_score:.3f} < {threshold}")
                return False

            check_count += 1
            self._ui_log(f"<b style='color:gray;'>[Passive Detect]</b> Check #{check_count} (elapsed: {elapsed:.1f}s)")

            if has_image:
                mask_regions = getattr(action, "mask_regions", None)
                teaching_window_width = getattr(action, "teaching_window_width", None)
                teaching_window_height = getattr(action, "teaching_window_height", None)
                image_result, score = self._find_image(
                    action.image_path,
                    threshold=threshold,
                    multiscale_enabled=False,
                    mask_regions=mask_regions,
                    teaching_window_width=teaching_window_width,
                    teaching_window_height=teaching_window_height,
                )
                best_score = max(best_score, score)
                if image_result is not None:
                    self._ui_log(f"<b style='color:green;'>[Passive Detect]</b> ✓ Tìm thấy ảnh!")
                    self._ui_log(f"<b style='color:green;'>[Passive Detect]</b> Score: {score:.3f} >= {threshold}")
                    self._ui_log(f"<b style='color:green;'>[Passive Detect]</b> Elapsed: {elapsed:.1f}s")
                    return True
                else:
                    self._ui_log(f"<b style='color:gray;'>[Passive Detect]</b> Score: {score:.3f} < {threshold}")

            sleep_end = time.time() + check_interval
            while time.time() < sleep_end:
                eng = self._get_engine()
                if eng and (not eng.is_running or eng.should_stop_completely):
                    self._ui_log("<b style='color:orange;'>[Passive Detect]</b> Engine stopped during sleep")
                    return None
                time.sleep(0.1)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_roi(self, frame: np.ndarray, action) -> np.ndarray:
        """Extract ROI from frame based on action settings."""
        use_fixed_roi = bool(getattr(action, 'use_fixed_roi', False))
        self._ui_log(f"<b style='color:blue;'>[Passive Debug]</b> use_fixed_roi = {use_fixed_roi}")

        if use_fixed_roi:
            roi_x = int(getattr(action, 'roi_x', 0) or 0)
            roi_y = int(getattr(action, 'roi_y', 0) or 0)
            roi_w = int(getattr(action, 'roi_w', 200) or 200)
            roi_h = int(getattr(action, 'roi_h', 100) or 100)
            self._ui_log(f"<b style='color:blue;'>[Passive Debug]</b> ROI coordinates: x={roi_x}, y={roi_y}, w={roi_w}, h={roi_h}")
            h, w = frame.shape[:2]
            x1 = max(0, min(roi_x, w - 1))
            y1 = max(0, min(roi_y, h - 1))
            x2 = min(w, x1 + roi_w)
            y2 = min(h, y1 + roi_h)
            if x2 > x1 and y2 > y1:
                self._ui_log(f"<b style='color:green;'>[Passive]</b> Using fixed ROI at ({x1},{y1}) size {x2-x1}x{y2-y1}")
                return frame[y1:y2, x1:x2]
            self._ui_log("<b style='color:orange;'>[Passive]</b> Invalid fixed ROI coordinates, using full frame")
            return frame

        if hasattr(action, 'image_path') and action.image_path and os.path.exists(action.image_path):
            self._ui_log(f"<b style='color:blue;'>[Passive]</b> Using teaching image: {os.path.basename(action.image_path)}")
            threshold = float(getattr(action, "match_threshold", 0.8))
            ms_enabled = bool(getattr(action, "multiscale_enabled", True))
            mask_regions = getattr(action, "mask_regions", None)
            teaching_window_width = getattr(action, "teaching_window_width", None)
            teaching_window_height = getattr(action, "teaching_window_height", None)
            image_result, confidence = self._find_image(
                action.image_path,
                threshold=threshold,
                multiscale_enabled=ms_enabled,
                mask_regions=mask_regions,
                teaching_window_width=teaching_window_width,
                teaching_window_height=teaching_window_height,
            )
            if image_result and confidence >= threshold and len(image_result) >= 4:
                top_left_x, top_left_y, img_w, img_h = image_result[:4]
                h, w = frame.shape[:2]
                x1 = max(0, top_left_x)
                y1 = max(0, top_left_y)
                x2 = min(w, top_left_x + img_w)
                y2 = min(h, top_left_y + img_h)
                if x2 > x1 and y2 > y1:
                    self._ui_log(f"<b style='color:green;'>[Passive]</b> Found ROI at ({x1},{y1}) size {x2-x1}x{y2-y1}, confidence: {confidence:.3f}")
                    return frame[y1:y2, x1:x2]
            self._ui_log(f"<b style='color:orange;'>[Passive]</b> Teaching image not found (confidence: {confidence:.3f} < {threshold}), using full frame")
            return frame

        self._ui_log("<b style='color:gray;'>[Passive]</b> No ROI method specified, using full frame")
        return frame

    def _run_gemini(self, text: str, action) -> Optional[str]:
        """Run Gemini processing if enabled."""
        if not bool(getattr(action, "gemini_enabled", False)):
            self._ui_log(f"<b style='color:gray;'>[Passive]</b> Gemini disabled (gemini_enabled={getattr(action, 'gemini_enabled', False)})")
            return None

        self._ui_log("<b style='color:blue;'>[Passive]</b> Gemini enabled, processing...")
        gemini_out = self._gemini_processor.process(text, action, overall_timeout_s=30.0)
        if gemini_out:
            self._ui_log(
                f"<b>[Passive Gemini]</b> Result length: {len(gemini_out)} chars<br>"
                f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(gemini_out)}</pre>"
            )
        else:
            self._ui_log("<b style='color:orange;'>[Passive Gemini]</b> No result from Gemini")
        return gemini_out

    def _send_notification(self, text: str, gemini_out: Optional[str], action, engine_used: str) -> None:
        """Send Telegram notification if enabled."""
        notification_content = gemini_out if gemini_out else text
        if not notification_content:
            return

        log_engine = "Gemini" if gemini_out else "OCR"
        self._log_manager.log_ocr_data(notification_content, log_engine)

        required_keywords = str(getattr(action, "notification_filter_keywords", "") or "")
        matching_sentences = self._text_filter.get_matching_sentences(notification_content, required_keywords)

        if matching_sentences:
            filtered_text = ". ".join(matching_sentences) + "."
            self._ui_log(f"<b style='color:green;'>[Telegram]</b> Found {len(matching_sentences)} matching sentence(s), sending notification...")
            self._telegram_notifier.send(action, filtered_text, is_gemini=bool(gemini_out))
            self._text_filter.mark_sent(notification_content)
        else:
            self._ui_log(f"<b style='color:orange;'>[Telegram]</b> No sentences matched filter (missing required keywords)")

        cleanup_result = self._log_manager.check_and_cleanup()
        if cleanup_result is not None:
            self._ui_log(f"<b style='color:blue;'>[LogManager]</b> Cleanup performed: deleted {cleanup_result} log files")

    def _show_cached_results(self, last_ocr_text: str, last_gemini_result: str,
                              keywords: list, keywords_csv: str, action, key: str) -> None:
        """Show cached OCR/Gemini results for unchanged frames."""
        if last_ocr_text:
            self._ui_log(
                f"<b>[Passive OCR - Cached]</b> Text length: {len(last_ocr_text)} chars<br>"
                f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(last_ocr_text)}</pre>"
            )
        else:
            self._ui_log("<b style='color:gray;'>[Passive OCR - Cached]</b> No cached OCR text")

        if last_gemini_result:
            self._ui_log(
                f"<b>[Passive Gemini - Cached]</b> Result length: {len(last_gemini_result)} chars<br>"
                f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(last_gemini_result)}</pre>"
            )

        if keywords and last_ocr_text:
            lower_text = last_ocr_text.lower()
            hit = any(k in lower_text for k in keywords)
            matched_keywords = [k for k in keywords if k in lower_text]
            self._ui_log(f"<b>[Passive Keyword - Cached]</b> {'CÓ' if hit else 'KHÔNG'} (keywords: {keywords_csv})")
            if matched_keywords:
                self._ui_log(f"<b style='color:green;'>[Passive Keyword - Cached]</b> Matched: {matched_keywords}")

