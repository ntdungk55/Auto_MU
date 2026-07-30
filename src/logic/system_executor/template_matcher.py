"""Template Matcher - Template matching logic extracted from SystemExecutor."""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, Callable


def _imread_unicode(filepath: str, flags=cv2.IMREAD_COLOR) -> Optional[np.ndarray]:
    """Read image with Unicode path support using imdecode."""
    try:
        with open(filepath, 'rb') as f:
            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
        return cv2.imdecode(file_bytes, flags)
    except Exception as e:
        print(f"[ERROR] Cannot read image {filepath}: {e}")
        return None


def _format_score(score: float) -> str:
    """Format score safely, handling inf/nan values."""
    try:
        if not isinstance(score, (int, float)):
            return "0.000"
        if not (-1e10 < score < 1e10):
            return "1.000" if score > 0 else "0.000"
        score = min(max(float(score), 0.0), 1.0)
        return f"{score:.3f}"
    except Exception:
        return "0.000"


@dataclass
class DetectionResult:
    """Generic detection result for image-based detectors."""
    found: bool
    score: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h) in window coords
    scale: float = 1.0
    raw: Optional[dict] = None


class TemplateMatcher:
    """Template matching logic with caching, multiscale, mask, and preprocessing support."""

    def __init__(self, ui_log_func: Callable[[str], None]):
        """Initialize TemplateMatcher.

        Args:
            ui_log_func: Function to log UI messages
        """
        self._ui_log = ui_log_func

        # Template caches
        self._template_gray_cache: dict[str, np.ndarray] = {}
        self._template_scaled_cache: dict[tuple, np.ndarray] = {}
        self._last_match: dict[tuple[str, bool], dict] = {}
        self._last_match_stats: dict[tuple[str, bool], dict] = {}

        # Cache size limits
        self._max_template_cache_size = 50
        self._max_scaled_cache_size = 200

    # ── Cache management ──────────────────────────────────────────────────────

    def clear_last_match_cache(self) -> None:
        """Clear cached last match positions."""
        try:
            self._last_match.clear()
        except Exception:
            pass
        try:
            self._last_match_stats.clear()
        except Exception:
            pass

    def clear_all_caches(self) -> None:
        """Clear all template caches and release numpy arrays."""
        import gc
        for key in list(self._template_gray_cache.keys()):
            try:
                arr = self._template_gray_cache.pop(key, None)
                del arr
            except Exception:
                pass
        for key in list(self._template_scaled_cache.keys()):
            try:
                arr = self._template_scaled_cache.pop(key, None)
                del arr
            except Exception:
                pass
        self._template_gray_cache.clear()
        self._template_scaled_cache.clear()
        self._last_match.clear()
        self._last_match_stats.clear()
        gc.collect()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _load_template_gray(self, template_path: str) -> Optional[np.ndarray]:
        """Load template from disk once and cache its grayscale form."""
        if not template_path:
            return None
        if template_path in self._template_gray_cache:
            return self._template_gray_cache[template_path]

        if len(self._template_gray_cache) >= self._max_template_cache_size:
            oldest = list(self._template_gray_cache.keys())[:10]
            for k in oldest:
                self._template_gray_cache.pop(k, None)
            self._ui_log(f"<b style='color:blue;'>[Cache]</b> Purged {len(oldest)} old template entries")

        templ_full = _imread_unicode(template_path, cv2.IMREAD_COLOR)
        if templ_full is None:
            return None
        templ_gray = cv2.cvtColor(templ_full, cv2.COLOR_BGR2GRAY)
        self._template_gray_cache[template_path] = templ_gray
        return templ_gray

    def _get_scaled_template(self, template_path: str, ignore_text: bool, scale: float, base_scale: float) -> Optional[np.ndarray]:
        """Get cached scaled template."""
        key = (template_path, bool(ignore_text), float(scale), float(base_scale))
        if key in self._template_scaled_cache:
            return self._template_scaled_cache[key]

        if len(self._template_scaled_cache) >= self._max_scaled_cache_size:
            oldest = list(self._template_scaled_cache.keys())[:20]
            for k in oldest:
                self._template_scaled_cache.pop(k, None)
            self._ui_log(f"<b style='color:blue;'>[Cache]</b> Purged {len(oldest)} old scaled template entries")

        base = self._load_template_gray(template_path)
        if base is None:
            return None

        templ = base
        if abs(base_scale - 1.0) > 1e-9:
            templ = cv2.resize(templ, (0, 0), fx=base_scale, fy=base_scale, interpolation=cv2.INTER_LINEAR)

        s = float(scale)
        if abs(s - 1.0) < 1e-9:
            templ_s = templ
        else:
            new_w = max(5, int(templ.shape[1] * s))
            new_h = max(5, int(templ.shape[0] * s))
            templ_s = cv2.resize(templ, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        self._template_scaled_cache[key] = templ_s
        return templ_s

    def _iter_scales_adaptive(self, template_path: str, ignore_text: bool, multiscale_enabled: bool,
                               smin: float, smax: float, step: float) -> list[float]:
        """Prefer last used scale first to reduce total trials."""
        if not multiscale_enabled:
            return [1.0]
        try:
            smin = float(smin)
            smax = float(smax)
            step = float(step) if float(step) > 0 else 0.05
            if smax < smin:
                smin, smax = smax, smin
        except Exception:
            return [1.0]

        last = self._last_match.get((template_path, bool(ignore_text)))
        if last and isinstance(last, dict):
            try:
                last_s = float(last.get("scale", 1.0))
            except Exception:
                last_s = 1.0
            candidates = [last_s]
            for k in (1, 2):
                candidates.append(last_s - k * step)
                candidates.append(last_s + k * step)
            out = []
            seen: set[float] = set()
            for s in candidates + [1.0]:
                if s < smin - 1e-9 or s > smax + 1e-9:
                    continue
                ss = round(float(s), 4)
                if ss not in seen:
                    seen.add(ss)
                    out.append(ss)
            if out:
                return out

        scales = []
        s = smin
        while s <= smax + 1e-9:
            scales.append(round(s, 4))
            s += step
        if 1.0 not in scales:
            scales.append(1.0)
        return sorted(set(scales))

    def _iter_rois_adaptive(self, win_w: int, win_h: int, template_path: str, ignore_text: bool) -> list[tuple]:
        """Start from last match rect expanded by margins; grow to full window."""
        last = self._last_match.get((template_path, bool(ignore_text)))
        if not last:
            return [(0, 0, win_w, win_h)]
        try:
            x = int(last.get("x", 0))
            y = int(last.get("y", 0))
            w = int(last.get("w", win_w))
            h = int(last.get("h", win_h))
        except Exception:
            return [(0, 0, win_w, win_h)]

        margins = [40, 120, 240, 480]
        rois = []
        for m in margins:
            x0 = max(0, x - m)
            y0 = max(0, y - m)
            x1 = min(win_w, x + w + m)
            y1 = min(win_h, y + h + m)
            rois.append((x0, y0, x1 - x0, y1 - y0))
        rois.append((0, 0, win_w, win_h))

        out = []
        seen: set = set()
        for r in rois:
            if r not in seen and r[2] > 0 and r[3] > 0:
                seen.add(r)
                out.append(r)
        return out

    def create_mask_array(self, template: np.ndarray, mask_regions: list) -> np.ndarray:
        """Create mask array from mask regions for template matching.

        Args:
            template: Template image (grayscale)
            mask_regions: List of {"x": int, "y": int, "w": int, "h": int}

        Returns:
            Mask array (255 = match, 0 = ignore)
        """
        h, w = template.shape[:2]
        mask = np.ones((h, w), dtype=np.uint8) * 255
        for region in mask_regions:
            try:
                x = int(region.get("x", 0))
                y = int(region.get("y", 0))
                rw = int(region.get("w", 0))
                rh = int(region.get("h", 0))
                x = max(0, min(w, x))
                y = max(0, min(h, y))
                x2 = max(0, min(w, x + rw))
                y2 = max(0, min(h, y + rh))
                if x2 > x and y2 > y:
                    mask[y:y2, x:x2] = 0
            except Exception:
                continue
        return mask

    # ── Public matching API ───────────────────────────────────────────────────

    def match_adaptive(
        self,
        screenshot_bgr: np.ndarray,
        template_path: str,
        threshold: float = 0.8,
        ignore_text: bool = False,
        multiscale_enabled: bool = True,
        multiscale_min: float = 0.70,
        multiscale_max: float = 1.30,
        multiscale_step: float = 0.05,
        mask_regions: Optional[list] = None,
        preprocessing_algorithms: Optional[list] = None,
        teaching_window_width: int = 800,
        teaching_window_height: int = 600,
        apply_preprocessing_fn: Optional[Callable] = None,
    ) -> tuple:
        """Optimized adaptive matching with ROI, scale caching, mask, and preprocessing.

        Args:
            screenshot_bgr: BGR screenshot (already captured)
            template_path: Path to template image
            threshold: Match threshold (0.0-1.0)
            ignore_text: Legacy parameter (unused)
            multiscale_enabled: Enable multiscale matching
            multiscale_min: Minimum scale factor
            multiscale_max: Maximum scale factor
            multiscale_step: Scale step
            mask_regions: List of regions to ignore in template
            preprocessing_algorithms: Preprocessing algorithm configs
            teaching_window_width: Teaching window width for resize
            teaching_window_height: Teaching window height for resize
            apply_preprocessing_fn: Optional callable(img_bgr, algorithms) -> img_bgr

        Returns:
            (result_tuple_or_None, score_float)
        """
        screenshot_gray = None
        base_mask = None

        try:
            original_height, original_width = screenshot_bgr.shape[:2]
            target_width = max(1, int(teaching_window_width) if teaching_window_width else 800)
            target_height = max(1, int(teaching_window_height) if teaching_window_height else 600)

            scale_x = original_width / target_width if target_width > 0 else 1.0
            scale_y = original_height / target_height if target_height > 0 else 1.0

            teaching_w_str = f"{teaching_window_width}x{teaching_window_height}" if teaching_window_width and teaching_window_height else "N/A"
            self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Current window: {original_width}x{original_height}, Teaching window: {teaching_w_str}, Target: {target_width}x{target_height}")
            if original_width != target_width or original_height != target_height:
                self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Screenshot scale: {scale_x:.3f}x (W), {scale_y:.3f}x (H)")

            # Resize screenshot
            work_bgr = screenshot_bgr
            if original_width != target_width or original_height != target_height:
                work_bgr = cv2.resize(screenshot_bgr, (target_width, target_height), interpolation=cv2.INTER_AREA)

            # Apply preprocessing to screenshot
            if preprocessing_algorithms and apply_preprocessing_fn:
                work_bgr = apply_preprocessing_fn(work_bgr, preprocessing_algorithms)
                self._ui_log(f"<span style='color:blue;'>[Preprocessing]</span> Đã áp dụng {len(preprocessing_algorithms)} thuật toán cho screenshot")

            win_h0, win_w0 = work_bgr.shape[:2]
            base_scale = 1.0
            screenshot_gray = cv2.cvtColor(work_bgr, cv2.COLOR_BGR2GRAY)
            del work_bgr

            win_h = screenshot_gray.shape[0]
            win_w = screenshot_gray.shape[1]

            # Load and resize template
            template_bgr = _imread_unicode(template_path, cv2.IMREAD_COLOR)
            if template_bgr is None:
                return None, 0.0

            template_original_w = template_bgr.shape[1]
            template_original_h = template_bgr.shape[0]

            template_scale_x = 1.0
            template_scale_y = 1.0
            if teaching_window_width and teaching_window_height:
                try:
                    tw = float(teaching_window_width)
                    th = float(teaching_window_height)
                    if tw > 0 and th > 0:
                        template_scale_x = target_width / tw
                        template_scale_y = target_height / th
                except Exception:
                    pass

            if abs(template_scale_x - 1.0) > 1e-9 or abs(template_scale_y - 1.0) > 1e-9:
                tw = max(1, int(template_bgr.shape[1] * template_scale_x))
                th = max(1, int(template_bgr.shape[0] * template_scale_y))
                template_bgr = cv2.resize(template_bgr, (tw, th), interpolation=cv2.INTER_AREA)
                self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Template: {template_original_w}x{template_original_h} → {tw}x{th} (scale: {template_scale_x:.3f}x, {template_scale_y:.3f}x)")
            else:
                self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Template: {template_original_w}x{template_original_h} (no resize needed)")

            # Apply preprocessing to template
            if preprocessing_algorithms and apply_preprocessing_fn:
                template_bgr = apply_preprocessing_fn(template_bgr, preprocessing_algorithms)
                self._ui_log(f"<span style='color:blue;'>[Preprocessing]</span> Đã áp dụng {len(preprocessing_algorithms)} thuật toán cho template")

            template_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)

            if mask_regions and len(mask_regions) > 0:
                base_mask = self.create_mask_array(template_gray, mask_regions)

            best_val = -1.0
            best_loc = None
            best_wh = None
            used_rois = 0

            rois0 = self._iter_rois_adaptive(win_w0, win_h0, template_path, ignore_text)

            for (x0, y0, w0, h0) in rois0:
                used_rois += 1
                x = int(x0 * base_scale)
                y = int(y0 * base_scale)
                w = int(w0 * base_scale)
                h = int(h0 * base_scale)
                x = max(0, min(x, win_w - 1))
                y = max(0, min(y, win_h - 1))
                w = max(1, min(w, win_w - x))
                h = max(1, min(h, win_h - y))
                roi = screenshot_gray[y:y + h, x:x + w]

                templ_s = template_gray
                if templ_s is None:
                    continue
                if templ_s.shape[0] > roi.shape[0] or templ_s.shape[1] > roi.shape[1]:
                    continue

                mask_s = base_mask
                if mask_s is not None:
                    res = cv2.matchTemplate(roi, templ_s, cv2.TM_CCOEFF_NORMED, mask=mask_s)
                else:
                    res = cv2.matchTemplate(roi, templ_s, cv2.TM_CCOEFF_NORMED)

                _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(res)
                max_val = float(max_val)
                if not (0.0 <= max_val <= 1.0):
                    max_val = min(max(max_val, 0.0), 1.0)
                if max_val > best_val:
                    best_val = max_val
                    best_loc = (max_loc[0] + x, max_loc[1] + y)
                    best_wh = (templ_s.shape[1], templ_s.shape[0])

                if best_val >= float(threshold) and used_rois == 1:
                    break

            max_val = float(best_val) if best_val >= 0 else 0.0
            if best_loc is None or best_wh is None:
                self._last_match_stats[(template_path, bool(ignore_text))] = {"rois": used_rois, "win_w": win_w0, "win_h": win_h0}
                return None, max_val

            if max_val >= float(threshold):
                top_left_x = int(best_loc[0] * scale_x / base_scale)
                top_left_y = int(best_loc[1] * scale_y / base_scale)
                w_orig = int(best_wh[0] * scale_x)
                h_orig = int(best_wh[1] * scale_y)
                result = (top_left_x, top_left_y, w_orig, h_orig)
                self._last_match[(template_path, bool(ignore_text))] = {"x": top_left_x, "y": top_left_y, "w": w_orig, "h": h_orig}
                self._last_match_stats[(template_path, bool(ignore_text))] = {"rois": used_rois, "win_w": win_w0, "win_h": win_h0}
                return result, max_val

            self._last_match_stats[(template_path, bool(ignore_text))] = {"rois": used_rois, "win_w": win_w0, "win_h": win_h0}
            return None, max_val

        finally:
            try:
                if screenshot_gray is not None:
                    del screenshot_gray
            except Exception:
                pass
            try:
                if base_mask is not None:
                    del base_mask
            except Exception:
                pass

    def match_standard(
        self,
        screenshot_bgr: np.ndarray,
        template_path: str,
        threshold: float = 0.8,
        multiscale_enabled: bool = True,
        multiscale_min: float = 0.70,
        multiscale_max: float = 1.30,
        multiscale_step: float = 0.05,
        teaching_window_width: int = 800,
        teaching_window_height: int = 600,
    ) -> DetectionResult:
        """Standard (non-adaptive) template matching backend.

        Args:
            screenshot_bgr: BGR screenshot
            template_path: Path to template image
            threshold: Match threshold
            multiscale_enabled: Enable multiscale
            multiscale_min: Min scale
            multiscale_max: Max scale
            multiscale_step: Scale step
            teaching_window_width: Teaching window width
            teaching_window_height: Teaching window height

        Returns:
            DetectionResult
        """
        if screenshot_bgr is None:
            return DetectionResult(found=False, score=0.0)

        original_height, original_width = screenshot_bgr.shape[:2]
        target_width = max(1, int(teaching_window_width) if teaching_window_width else 800)
        target_height = max(1, int(teaching_window_height) if teaching_window_height else 600)

        scale_x = original_width / target_width if target_width > 0 else 1.0
        scale_y = original_height / target_height if target_height > 0 else 1.0

        teaching_w_str = f"{teaching_window_width}x{teaching_window_height}" if teaching_window_width and teaching_window_height else "N/A"
        self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Current window: {original_width}x{original_height}, Teaching window: {teaching_w_str}, Target: {target_width}x{target_height}")
        if original_width != target_width or original_height != target_height:
            self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Screenshot scale: {scale_x:.3f}x (W), {scale_y:.3f}x (H)")

        work = screenshot_bgr
        if original_width != target_width or original_height != target_height:
            work = cv2.resize(screenshot_bgr, (target_width, target_height), interpolation=cv2.INTER_AREA)

        screenshot_gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
        template_full = _imread_unicode(template_path, cv2.IMREAD_COLOR)
        if template_full is None:
            return DetectionResult(found=False, score=0.0)

        template_original_w = template_full.shape[1]
        template_original_h = template_full.shape[0]

        template_scale_x = 1.0
        template_scale_y = 1.0
        if teaching_window_width and teaching_window_height:
            try:
                tw = float(teaching_window_width)
                th = float(teaching_window_height)
                if tw > 0 and th > 0:
                    template_scale_x = target_width / tw
                    template_scale_y = target_height / th
            except Exception:
                pass

        if abs(template_scale_x - 1.0) > 1e-9 or abs(template_scale_y - 1.0) > 1e-9:
            tw = max(1, int(template_full.shape[1] * template_scale_x))
            th = max(1, int(template_full.shape[0] * template_scale_y))
            template_full = cv2.resize(template_full, (tw, th), interpolation=cv2.INTER_AREA)
            self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Template: {template_original_w}x{template_original_h} → {tw}x{th} (scale: {template_scale_x:.3f}x, {template_scale_y:.3f}x)")
        else:
            self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Template: {template_original_w}x{template_original_h} (no resize needed)")

        template_gray = cv2.cvtColor(template_full, cv2.COLOR_BGR2GRAY)

        best_val = -1.0
        best_loc = None
        best_scale = 1.0
        best_wh = None

        def _iter_scales() -> list[float]:
            if not multiscale_enabled:
                return [1.0]
            try:
                smin = float(multiscale_min)
                smax = float(multiscale_max)
                step = float(multiscale_step)
                if step <= 0:
                    step = 0.05
                if smax < smin:
                    smin, smax = smax, smin
                scales = []
                s = smin
                while s <= smax + 1e-9:
                    scales.append(round(s, 4))
                    s += step
                if 1.0 not in scales:
                    scales.append(1.0)
                return sorted(set(scales))
            except Exception:
                return [1.0]

        for s in _iter_scales():
            if abs(s - 1.0) < 1e-9:
                templ_s = template_gray
            else:
                new_w = max(5, int(template_gray.shape[1] * s))
                new_h = max(5, int(template_gray.shape[0] * s))
                templ_s = cv2.resize(template_gray, (new_w, new_h),
                                     interpolation=cv2.INTER_AREA if s < 1.0 else cv2.INTER_CUBIC)

            if templ_s.shape[0] > screenshot_gray.shape[0] or templ_s.shape[1] > screenshot_gray.shape[1]:
                continue

            result = cv2.matchTemplate(screenshot_gray, templ_s, cv2.TM_CCOEFF_NORMED)
            _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
            max_val = float(max_val)
            if not (0.0 <= max_val <= 1.0):
                max_val = min(max(max_val, 0.0), 1.0)
            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc
                best_scale = float(s)
                best_wh = (templ_s.shape[1], templ_s.shape[0])

        score = float(best_val) if best_val >= 0 else 0.0
        if best_loc is None or best_wh is None:
            return DetectionResult(found=False, score=score, raw={"scale_x": scale_x, "scale_y": scale_y})

        if score < float(threshold):
            return DetectionResult(
                found=False,
                score=score,
                bbox=(int(best_loc[0] * scale_x), int(best_loc[1] * scale_y),
                      int(best_wh[0] * scale_x), int(best_wh[1] * scale_y)),
                scale=best_scale,
                raw={"scale_x": scale_x, "scale_y": scale_y},
            )

        top_left_x = int(best_loc[0] * scale_x)
        top_left_y = int(best_loc[1] * scale_y)
        w0 = int(round(best_wh[0] * scale_x))
        h0 = int(round(best_wh[1] * scale_y))

        return DetectionResult(
            found=True,
            score=score,
            bbox=(top_left_x, top_left_y, w0, h0),
            scale=best_scale,
            raw={"scale_x": scale_x, "scale_y": scale_y},
        )
