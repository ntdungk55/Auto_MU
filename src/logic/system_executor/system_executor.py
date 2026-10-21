"""System Executor - Main orchestrator for automation actions."""

import os
import re
import sys
import time
import threading
import gc
import difflib
import unicodedata
import cv2
import numpy as np
from datetime import datetime

# Import modular components
from .ocr_engine import OCRFactory
from .ocr_preprocessor import OCRPreprocessor
from .template_matching_preprocessor import (
    TemplateMatchingPreprocessor,
    apply_rgb_range_filter_to_bgr,
)
from .window_capture import WindowCapture
from .mouse_controller import MouseController
from .gemini_processor import GeminiProcessor
from .telegram_notifier import TelegramNotifier
from .text_filter import TextFilter

try:
    from ..vision.yolo import YoloDetector
    from ..vision.yolo.exceptions import YoloError
except ImportError:
    from logic.vision.yolo import YoloDetector
    from logic.vision.yolo.exceptions import YoloError

# Import from parent logic module
try:
    from action_type import ActionType, AutoAction
    from window_detector import WindowDetector
    from log_manager import LogManager
except ImportError:
    from ..action_type import ActionType, AutoAction
    from ..window_detector import WindowDetector
    from ..log_manager import LogManager

try:
    import pytesseract
except Exception:
    pytesseract = None


def _imread_unicode(filepath: str, flags=cv2.IMREAD_COLOR):
    """Read image with Unicode path support using imdecode.
    
    cv2.imread does NOT support Unicode paths on Windows - it corrupts them.
    Always use open() + imdecode() for reliable Unicode path support.
    """
    try:
        with open(filepath, 'rb') as f:
            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, flags)
        return img
    except Exception as e:
        print(f"[ERROR] Cannot read image {filepath}: {e}")
        return None


def _format_score(score: float) -> str:
    """Format score safely, handling inf/nan values.
    
    Args:
        score: Score value from template matching (should be 0.0-1.0)
    
    Returns:
        Formatted string like "0.850" or "1.000" (capped to valid range)
    """
    try:
        # Handle inf/nan
        if not isinstance(score, (int, float)):
            return "0.000"
        if not (-1e10 < score < 1e10):  # Catch inf/-inf
            return "1.000" if score > 0 else "0.000"
        # Cap to valid range [0.0, 1.0]
        score = min(max(float(score), 0.0), 1.0)
        return f"{score:.3f}"
    except Exception:
        return "0.000"


def _configure_tesseract_cmd():
    """Try to locate tesseract.exe on Windows if it's installed but not in PATH."""
    if pytesseract is None:
        return

    def _iter_base_dirs() -> list[str]:
        """Candidate base dirs for locating bundled resources (dev + frozen builds)."""
        bases: list[str] = []
        try:
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass and isinstance(meipass, str):
                bases.append(meipass)
        except Exception:
            pass

        try:
            exe_dir = os.path.dirname(sys.executable)
            if exe_dir:
                bases.append(exe_dir)
        except Exception:
            pass

        try:
            bases.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        except Exception:
            pass

        try:
            bases.append(os.path.abspath(os.path.dirname(__file__)))
        except Exception:
            pass
        try:
            bases.append(os.getcwd())
        except Exception:
            pass

        seen = set()
        out: list[str] = []
        for b in bases:
            try:
                b2 = os.path.abspath(b)
            except Exception:
                b2 = b
            if b2 and b2 not in seen:
                seen.add(b2)
                out.append(b2)
        return out

    def _maybe_set_tessdata_prefix(tesseract_exe: str):
        """If we can locate tessdata folder, set TESSDATA_PREFIX for this process."""
        try:
            if os.environ.get("TESSDATA_PREFIX"):
                return
        except Exception:
            pass

        candidates: list[str] = []
        try:
            candidates.append(os.path.join(os.path.dirname(tesseract_exe), "tessdata"))
        except Exception:
            pass
        for base in _iter_base_dirs():
            candidates.append(os.path.join(base, "vendor", "tesseract", "tessdata"))
            candidates.append(os.path.join(base, "vendor", "Tesseract-OCR", "tessdata"))

        for td in candidates:
            try:
                if os.path.isdir(td):
                    os.environ["TESSDATA_PREFIX"] = td
                    return
            except Exception:
                continue

    try:
        current = getattr(pytesseract.pytesseract, "tesseract_cmd", None)
        if current and isinstance(current, str) and os.path.exists(current):
            _maybe_set_tessdata_prefix(current)
            return
    except Exception:
        pass

    try:
        env_cmd = os.environ.get("TESSERACT_CMD")
        if env_cmd and os.path.exists(env_cmd):
            pytesseract.pytesseract.tesseract_cmd = env_cmd
            _maybe_set_tessdata_prefix(env_cmd)
            return
    except Exception:
        pass

    candidates: list[str] = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe",
    ]
    for base in _iter_base_dirs():
        candidates.append(os.path.join(base, "vendor", "tesseract", "tesseract.exe"))
        candidates.append(os.path.join(base, "vendor", "Tesseract-OCR", "tesseract.exe"))
    for p in candidates:
        try:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                _maybe_set_tessdata_prefix(p)
                return
        except Exception:
            continue

_configure_tesseract_cmd()


from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class DetectionResult:
    """Generic detection result for image-based detectors.
    
    This abstraction makes it easier to plug in new detection backends
    (template matching, OCR-based, feature-based, AI, ...) without changing
    the higher level execution logic.
    """
    found: bool
    score: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h) in window coords
    scale: float = 1.0  # Detected scale relative to teaching/template
    raw: Optional[dict] = None  # Backend-specific debug info (scales tried, etc.)


class SystemExecutor:
    """Main orchestrator for automation actions."""
    
    def __init__(self, target_window_hwnd=None, ui_log_func=None):
        """Initialize SystemExecutor with modular components.
        
        Args:
            target_window_hwnd: Target window handle
            ui_log_func: Optional function to log UI messages (for test mode)
        """
        self.target_window_hwnd = target_window_hwnd
        self.window_detector = WindowDetector()
        self.engine = None  # Will be set by caller to check stop flags
        self._external_ui_log_func = ui_log_func  # Store external log function
        
        # Initialize modular components
        self.window_capture = WindowCapture(target_window_hwnd, self._ui_log)
        self.mouse_controller = MouseController(target_window_hwnd, self._ui_log)
        self.ocr_engine = OCRFactory.create("auto", self._ui_log)
        self.ocr_preprocessor = OCRPreprocessor
        self.gemini_processor = GeminiProcessor(self._ui_log)
        self.telegram_notifier = TelegramNotifier(self._ui_log)
        self.text_filter = TextFilter()
        self.log_manager = LogManager(cleanup_interval_hours=1.0)
        
        # User input detector (set by ToolRunner)
        self._user_input_detector = None
        
        # Template matching caches
        self._template_gray_cache: dict[str, np.ndarray] = {}
        self._template_scaled_cache: dict[tuple[str, bool, float, float], np.ndarray] = {}
        self._last_match: dict[tuple[str, bool], dict] = {}
        self._last_match_stats: dict[tuple[str, bool], dict] = {}
        self._last_wait_diagnostics: dict | None = None
        
        # Cache size limits to prevent memory leaks
        self._max_template_cache_size = 50  # Max number of cached templates
        self._max_scaled_cache_size = 200   # Max number of scaled templates
        
        # Passive read cache
        self._passive_cache: dict[str, dict] = {}

    def release_all_modifier_keys(self):
        """Best-effort cleanup for stuck modifier keys."""
        try:
            self.mouse_controller.release_modifier_keys()
        except Exception:
            pass

        try:
            import ctypes
            user32 = ctypes.windll.user32
            key_up = 0x0002
            for vk_code in (0x12, 0x11, 0x10, 0x5B, 0x5C):
                try:
                    user32.keybd_event(vk_code, 0, key_up, 0)
                except Exception:
                    pass
        except Exception:
            pass
    
    def _focus_target_window(self) -> bool:
        """Focus target window before interactive actions.
        
        Uses AttachThreadInput workaround to bypass Windows foreground lock restrictions.
        
        Returns:
            True if window was focused successfully, False otherwise
        """
        if not self.target_window_hwnd:
            self._ui_log("<b style='color:red;'>[Focus]</b> Không có target window")
            return False
        
        try:
            import win32gui
            import win32con
            import win32process
            
            # Check if window exists and is valid
            if not win32gui.IsWindow(self.target_window_hwnd):
                self._ui_log("<b style='color:red;'>[Focus]</b> Window không tồn tại hoặc đã đóng")
                return False
            
            # Get window title for logging
            try:
                window_title = win32gui.GetWindowText(self.target_window_hwnd)
            except Exception:
                window_title = "Unknown"
            
            # Check if already focused - if yes, skip (avoid foreground lock issues)
            try:
                current_fg = win32gui.GetForegroundWindow()
                if current_fg == self.target_window_hwnd:
                    self._ui_log(f"<b style='color:green;'>[Focus]</b> ✓ Window đã được focus rồi, skip")
                    return True
            except Exception:
                pass
            
            # Check if window is minimized, restore it first
            try:
                if win32gui.IsIconic(self.target_window_hwnd):
                    self._ui_log(f"<b style='color:orange;'>[Focus]</b> Window bị minimize, đang restore...")
                    win32gui.ShowWindow(self.target_window_hwnd, win32con.SW_RESTORE)
                    time.sleep(0.1)  # Wait for restore animation
            except Exception as e:
                self._ui_log(f"<b style='color:orange;'>[Focus]</b> Không thể restore window: {e}")
            
            # Get current foreground window before focus
            try:
                current_fg = win32gui.GetForegroundWindow()
                current_fg_title = win32gui.GetWindowText(current_fg) if current_fg else "None"
            except Exception:
                current_fg = None
                current_fg_title = "Unknown"
            
            self._ui_log(f"<b style='color:cyan;'>[Focus]</b> Đang focus: '{window_title}' (hwnd={self.target_window_hwnd})")
            self._ui_log(f"<b style='color:gray;'>[Focus]</b> Window hiện tại: '{current_fg_title}' (hwnd={current_fg})")
            
            # TRICK: Simulate ALT key to bypass foreground lock
            # Windows allows SetForegroundWindow if user is "interacting" (ALT = interaction)
            try:
                import ctypes
                alt_pressed = False
                try:
                    # Press ALT (VK_MENU = 0x12)
                    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
                    alt_pressed = True
                    time.sleep(0.01)

                    # Now SetForegroundWindow should work
                    win32gui.SetForegroundWindow(self.target_window_hwnd)
                    time.sleep(0.05)
                finally:
                    if alt_pressed:
                        try:
                            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # KEYEVENTF_KEYUP = 2
                        except Exception:
                            pass
                    self.release_all_modifier_keys()
            except Exception as e:
                # Fallback: try direct SetForegroundWindow (may fail)
                self._ui_log(f"<b style='color:orange;'>[Focus]</b> ALT trick failed, trying direct: {e}")
                try:
                    win32gui.SetForegroundWindow(self.target_window_hwnd)
                    time.sleep(0.05)
                except Exception as e2:
                    self._ui_log(f"<b style='color:red;'>[Focus]</b> SetForegroundWindow failed: {e2}")
                    return False
            
            # Additional delay for window to stabilize
            time.sleep(0.1)
            
            # Verify focus was successful
            try:
                new_fg = win32gui.GetForegroundWindow()
                if new_fg == self.target_window_hwnd:
                    self._ui_log(f"<b style='color:green;'>[Focus]</b> ✓ Focus thành công")
                    return True
                else:
                    new_fg_title = win32gui.GetWindowText(new_fg) if new_fg else "None"
                    self._ui_log(f"<b style='color:red;'>[Focus]</b> ✗ Focus thất bại! Window hiện tại: '{new_fg_title}' (hwnd={new_fg})")
                    self._ui_log(f"<b style='color:orange;'>[Focus]</b> Có thể do: Windows foreground lock (click vào Kiro IDE?), game anti-cheat, hoặc cần quyền admin")
                    return False
            except Exception as e:
                self._ui_log(f"<b style='color:orange;'>[Focus]</b> Không thể verify focus: {e}")
                return True  # Assume success if can't verify
                
        except Exception as e:
            self._ui_log(f"<b style='color:red;'>[Focus]</b> Lỗi: {e}")
            print(f"[Focus] Error focusing window: {e}")
            return False
    
    def _ui_log(self, msg: str):
        """Log to UI or console."""
        # Try external log function first (for test mode)
        if self._external_ui_log_func:
            try:
                self._external_ui_log_func(msg)
                return
            except Exception:
                pass
        
        # Try engine signals
        try:
            if self.engine and hasattr(self.engine, "signals"):
                self.engine.signals.log.emit(msg)
                return
        except Exception:
            pass
        
        # Fallback to console
        print(msg)
    
    def set_target_window(self, hwnd):
        """Set target window handle."""
        self.target_window_hwnd = hwnd
        self.window_capture.set_target_window(hwnd)
        self.mouse_controller.set_target_window(hwnd)
    
    def set_user_input_detector(self, detector):
        """Set user input detector for tool_acting flag management.
        
        Args:
            detector: UserInputDetector instance or None
        """
        self._user_input_detector = detector
    
    def _set_tool_acting(self, is_acting: bool):
        """Set tool_acting flag on user input detector.
        
        Args:
            is_acting: True when tool is sending input, False otherwise
        """
        if self._user_input_detector:
            try:
                self._user_input_detector.set_tool_acting(is_acting)
            except Exception:
                pass
    
    def capture_window_screenshot(self) -> np.ndarray | None:
        """Capture window screenshot."""
        return self.window_capture.capture()
    
    def clear_last_match_cache(self):
        """Clear cached last match positions."""
        try:
            self._last_match.clear()
        except Exception:
            pass
        try:
            self._last_match_stats.clear()
        except Exception:
            pass
        self._last_wait_diagnostics = None
    
    def clear_all_caches(self):
        """Clear all caches and force garbage collection to prevent memory leaks.
        
        SAFE: This method explicitly deletes numpy arrays before clearing cache
        to ensure proper memory release. Should only be called when no operations
        are using the cached data.
        """
        try:
            # Step 1: Explicitly delete numpy arrays in template_gray_cache
            gray_keys = list(self._template_gray_cache.keys())
            for key in gray_keys:
                try:
                    arr = self._template_gray_cache.pop(key, None)
                    if arr is not None and isinstance(arr, np.ndarray):
                        # Explicitly set to None to release reference
                        arr = None
                        del arr
                except Exception:
                    pass
            
            # Step 2: Explicitly delete numpy arrays in template_scaled_cache
            scaled_keys = list(self._template_scaled_cache.keys())
            for key in scaled_keys:
                try:
                    arr = self._template_scaled_cache.pop(key, None)
                    if arr is not None and isinstance(arr, np.ndarray):
                        # Explicitly set to None to release reference
                        arr = None
                        del arr
                except Exception:
                    pass
            
            # Step 3: Clear remaining cache dictionaries
            self._template_gray_cache.clear()
            self._template_scaled_cache.clear()
            self._last_match.clear()
            self._last_match_stats.clear()
            self._last_wait_diagnostics = None
            
            # Step 4: Clear passive cache (may contain numpy arrays)
            passive_keys = list(self._passive_cache.keys())
            for key in passive_keys:
                try:
                    val = self._passive_cache.pop(key, None)
                    if val is not None:
                        val = None
                        del val
                except Exception:
                    pass
            self._passive_cache.clear()
            
            # Step 5: Force garbage collection to reclaim memory immediately
            gc.collect()
            
            self._ui_log("<b style='color:blue;'>[Memory]</b> Cleared all caches and forced GC")
        except Exception as e:
            self._ui_log(f"<b style='color:orange;'>[Memory]</b> Cache clear error: {e}")
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def get_last_wait_diagnostics(self) -> dict | None:
        """Return diagnostics for the last execute_with_timeout call."""
        try:
            return dict(self._last_wait_diagnostics) if self._last_wait_diagnostics else None
        except Exception:
            return None
    
    @staticmethod
    def _escape_html(s: str) -> str:
        """Escape HTML special characters."""
        try:
            if s is None:
                return ""
            s = str(s)
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
        except Exception as e:
            print(f"[_escape_html] ERROR: {e}, input type={type(s)}")
            return str(s) if s is not None else ""

    # ============ Template Matching Methods ============
    
    def _load_template_gray(self, template_path: str) -> np.ndarray | None:
        """Load template from disk once and cache its grayscale form."""
        if not template_path:
            return None
        if template_path in self._template_gray_cache:
            return self._template_gray_cache[template_path]
        
        # Check cache size limit
        if len(self._template_gray_cache) >= self._max_template_cache_size:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self._template_gray_cache.keys())[:10]
            for key in oldest_keys:
                self._template_gray_cache.pop(key, None)
            self._ui_log(f"<b style='color:blue;'>[Cache]</b> Purged {len(oldest_keys)} old template entries")
        
        templ_full = _imread_unicode(template_path, cv2.IMREAD_COLOR)
        if templ_full is None:
            return None
        templ_gray = cv2.cvtColor(templ_full, cv2.COLOR_BGR2GRAY)
        self._template_gray_cache[template_path] = templ_gray
        return templ_gray
    
    def _get_scaled_template(self, template_path: str, ignore_text: bool, scale: float, base_scale: float) -> np.ndarray | None:
        """Get cached scaled template in the matching domain."""
        key = (template_path, bool(ignore_text), float(scale), float(base_scale))
        if key in self._template_scaled_cache:
            return self._template_scaled_cache[key]

        # Check cache size limit
        if len(self._template_scaled_cache) >= self._max_scaled_cache_size:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self._template_scaled_cache.keys())[:20]
            for cache_key in oldest_keys:
                self._template_scaled_cache.pop(cache_key, None)
            self._ui_log(f"<b style='color:blue;'>[Cache]</b> Purged {len(oldest_keys)} old scaled template entries")

        base = self._load_template_gray(template_path)
        if base is None:
            return None

        templ = base
        # Removed hardcoded GaussianBlur preprocessing
        # User can apply custom preprocessing via TemplateMatchingPreprocessor before matching

        if abs(base_scale - 1.0) > 1e-9:
            # Use INTER_LINEAR as default (good balance between speed and quality)
            templ = cv2.resize(templ, (0, 0), fx=base_scale, fy=base_scale, interpolation=cv2.INTER_LINEAR)

        s = float(scale)
        if abs(s - 1.0) < 1e-9:
            templ_s = templ
        else:
            new_w = max(5, int(templ.shape[1] * s))
            new_h = max(5, int(templ.shape[0] * s))
            # Use INTER_LINEAR as default (good balance between speed and quality)
            templ_s = cv2.resize(templ, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        self._template_scaled_cache[key] = templ_s
        return templ_s
    
    def _iter_scales_adaptive(self, template_path: str, ignore_text: bool, multiscale_enabled: bool, smin: float, smax: float, step: float):
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
            seen = set()
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
    
    def _create_mask_array(self, template: np.ndarray, mask_regions: list) -> np.ndarray:
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
                
                # Clamp to template bounds
                x = max(0, min(w, x))
                y = max(0, min(h, y))
                x2 = max(0, min(w, x + rw))
                y2 = max(0, min(h, y + rh))
                
                # Set mask region to 0 (ignore)
                if x2 > x and y2 > y:
                    mask[y:y2, x:x2] = 0
            except Exception:
                continue
        
        return mask
    
    def _apply_preprocessing_algorithms(self, img_bgr: np.ndarray, algorithms: list) -> np.ndarray:
        """Apply preprocessing algorithms to image.
        
        Args:
            img_bgr: Input image in BGR format
            algorithms: List of algorithm configs from action.template_matching_algorithms or action.ocr_algorithms
        
        Returns:
            Preprocessed image in BGR format
        """
        if not algorithms or not isinstance(algorithms, list):
            return img_bgr
        
        try:
            # Apply each algorithm in sequence using TemplateMatchingPreprocessor
            preprocessor = TemplateMatchingPreprocessor(img_bgr, self._ui_log)
            
            for algo in algorithms:
                if not isinstance(algo, dict):
                    continue
                
                config = algo.get("config", {})
                if not config:
                    continue

                if config.get("rgb_range_filter"):
                    preprocessor.img = apply_rgb_range_filter_to_bgr(preprocessor.img, config)
                
                # Apply binary threshold first if specified
                if config.get("binary_threshold"):
                    threshold_value = config.get("threshold_value", 127)
                    threshold_type = config.get("threshold_type", 0)
                    
                    gray = cv2.cvtColor(preprocessor.img, cv2.COLOR_BGR2GRAY)
                    thresh_type = cv2.THRESH_BINARY if threshold_type == 0 else cv2.THRESH_BINARY_INV
                    _, binary = cv2.threshold(gray, threshold_value, 255, thresh_type)
                    preprocessor.img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
                    continue

                if config.get("adaptive_threshold_mean") or config.get("adaptive_threshold_gaussian"):
                    adaptive_threshold_type = config.get("adaptive_threshold_type", 0)
                    block_size = int(config.get("adaptive_block_size", 11) or 11)
                    c_value = int(config.get("adaptive_c", 2) or 2)
                    max_value = int(config.get("adaptive_max_value", 255) or 255)

                    if block_size < 3:
                        block_size = 3
                    if block_size % 2 == 0:
                        block_size += 1

                    gray = cv2.cvtColor(preprocessor.img, cv2.COLOR_BGR2GRAY)
                    thresh_type = cv2.THRESH_BINARY if adaptive_threshold_type == 0 else cv2.THRESH_BINARY_INV
                    adaptive_method = (
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C
                        if config.get("adaptive_threshold_gaussian")
                        else cv2.ADAPTIVE_THRESH_MEAN_C
                    )
                    adaptive = cv2.adaptiveThreshold(
                        gray,
                        max_value,
                        adaptive_method,
                        thresh_type,
                        block_size,
                        c_value,
                    )
                    preprocessor.img = cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR)
                    continue
                
                # Apply grayscale if specified
                if config.get("grayscale"):
                    gray = cv2.cvtColor(preprocessor.img, cv2.COLOR_BGR2GRAY)
                    preprocessor.img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                    continue
                
                # Basic algorithms
                if config.get("upscale"):
                    preprocessor = preprocessor.upscale(config["upscale"])
                if config.get("enhance_contrast"):
                    contrast_level = config.get("contrast_level", 3.0)
                    preprocessor = preprocessor.enhance_contrast(contrast_level)
                if config.get("sharpen"):
                    sharpen_strength = config.get("sharpen_strength", 1.5)
                    preprocessor = preprocessor.sharpen(sharpen_strength)
                if config.get("denoise"):
                    denoise_strength = config.get("denoise_strength", 9)
                    preprocessor = preprocessor.denoise(denoise_strength)
                
                # Morphological operations
                if config.get("morphological_opening"):
                    kernel_size = config.get("opening_kernel_size", 3)
                    preprocessor = preprocessor.morphological_opening(kernel_size)
                if config.get("morphological_closing"):
                    kernel_size = config.get("closing_kernel_size", 3)
                    preprocessor = preprocessor.morphological_closing(kernel_size)
                
                # Advanced noise removal
                if config.get("remove_small_components"):
                    min_area = config.get("min_component_area", 50)
                    preprocessor = preprocessor.remove_small_components(min_area)
                if config.get("median_filter"):
                    kernel_size = config.get("median_kernel_size", 5)
                    preprocessor = preprocessor.median_filter(kernel_size)
                if config.get("edge_preserving_filter"):
                    flags = config.get("epf_flags", 1)
                    sigma_s = config.get("epf_sigma_s", 50.0)
                    sigma_r = config.get("epf_sigma_r", 0.4)
                    preprocessor = preprocessor.edge_preserving_filter(flags, sigma_s, sigma_r)
                if config.get("nlm_denoising"):
                    h = config.get("nlm_h", 10.0)
                    template_window_size = config.get("nlm_template_window_size", 7)
                    search_window_size = config.get("nlm_search_window_size", 21)
                    preprocessor = preprocessor.nlm_denoising(h, template_window_size, search_window_size)
                
                # Template matching specific algorithms
                if config.get("gaussian_blur"):
                    kernel_size = config.get("gaussian_kernel_size", 5)
                    sigma_x = config.get("gaussian_sigma_x", 0.0)
                    preprocessor = preprocessor.gaussian_blur(kernel_size, sigma_x)
                if config.get("histogram_equalization"):
                    preprocessor = preprocessor.histogram_equalization()
                if config.get("canny_edge_detection"):
                    low_threshold = config.get("canny_low_threshold", 50)
                    high_threshold = config.get("canny_high_threshold", 150)
                    preprocessor = preprocessor.canny_edge_detection(low_threshold, high_threshold)
            
            return preprocessor.build()
        except Exception as e:
            self._ui_log(f"<span style='color:orange;'>[Preprocessing]</span> Lỗi: {e}")
            return img_bgr
    
    def _iter_rois_adaptive(self, win_w: int, win_h: int, template_path: str, ignore_text: bool):
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
        seen = set()
        for r in rois:
            if r not in seen and r[2] > 0 and r[3] > 0:
                seen.add(r)
                out.append(r)
        return out
    
    def find_image_in_window(self, template_path: str, threshold: float = 0.8) -> tuple:
        """Find image in window, return (top_left_x, top_left_y, width, height) or None."""
        if not self.target_window_hwnd:
            return None
        
        screenshot_bgr = self.capture_window_screenshot()
        if screenshot_bgr is None:
            return None
        
        screenshot_gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
        template_full = _imread_unicode(template_path, cv2.IMREAD_COLOR)
        if template_full is None:
            return None
        
        template = cv2.cvtColor(template_full, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            h, w = template.shape
            top_left_x = max_loc[0]
            top_left_y = max_loc[1]
            return (top_left_x, top_left_y, w, h)
        return None
    
    def find_image_in_window_with_score(
        self,
        template_path: str,
        threshold: float = 0.8,
        ignore_text: bool = False,
        multiscale_enabled: bool = True,
        multiscale_min: float = 0.70,
        multiscale_max: float = 1.30,
        multiscale_step: float = 0.05,
        use_adaptive: bool = True,
        mask_regions: list = None,
        preprocessing_algorithms: list = None,
        teaching_window_width: int = 800,
        teaching_window_height: int = 600,
    ):
        """Find image with score, return (result, max_val).
        
        Args:
            teaching_window_width: Target window width for resizing screenshot (default: 800)
            teaching_window_height: Target window height for resizing screenshot (default: 600)
        """
        if not self.target_window_hwnd:
            return None, 0.0

        if bool(use_adaptive):
            try:
                return self.find_image_in_window_with_score_adaptive(
                    template_path,
                    threshold=threshold,
                    ignore_text=ignore_text,
                    multiscale_enabled=multiscale_enabled,
                    multiscale_min=multiscale_min,
                    multiscale_max=multiscale_max,
                    multiscale_step=multiscale_step,
                    mask_regions=mask_regions,
                    preprocessing_algorithms=preprocessing_algorithms,
                    teaching_window_width=teaching_window_width,
                    teaching_window_height=teaching_window_height,
                )
            except Exception:
                pass

        # Capture window screenshot
        screenshot_bgr = self.capture_window_screenshot()
        if screenshot_bgr is None:
            return None, 0.0

        # Delegate the actual template matching to a reusable helper to prepare
        # for future detection backends (OCR / feature-based / AI).
        detection = self._run_template_matching(
            screenshot_bgr=screenshot_bgr,
            template_path=template_path,
            threshold=threshold,
            multiscale_enabled=multiscale_enabled,
            multiscale_min=multiscale_min,
            multiscale_max=multiscale_max,
            multiscale_step=multiscale_step,
            teaching_window_width=teaching_window_width,
            teaching_window_height=teaching_window_height,
        )

        if not detection or not detection.found or not detection.bbox:
            return None, detection.score if detection else 0.0

        x, y, w, h = detection.bbox
        return (x, y, w, h, detection.scale), detection.score
    
    def find_image_in_window_with_score_adaptive(
        self,
        template_path: str,
        threshold: float = 0.8,
        ignore_text: bool = False,
        multiscale_enabled: bool = True,
        multiscale_min: float = 0.70,
        multiscale_max: float = 1.30,
        multiscale_step: float = 0.05,
        mask_regions: list = None,
        preprocessing_algorithms: list = None,
        teaching_window_width: int = 800,
        teaching_window_height: int = 600,
    ):
        """Optimized matching: cached templates + adaptive ROI + prefer last scale + mask support + preprocessing.
        
        MEMORY SAFE: Explicitly cleans up screenshot arrays after use to prevent memory leaks.
        
        Args:
            template_path: Path to template image
            threshold: Match threshold (0.0-1.0)
            ignore_text: Legacy parameter (not used)
            multiscale_enabled: Enable multiscale matching
            multiscale_min: Minimum scale factor
            multiscale_max: Maximum scale factor
            multiscale_step: Scale step
            mask_regions: List of regions to ignore in template
            preprocessing_algorithms: List of preprocessing algorithms to apply (from action.template_matching_algorithms)
            teaching_window_width: Target window width for resizing screenshot (default: 800)
            teaching_window_height: Target window height for resizing screenshot (default: 600)
        """
        if not self.target_window_hwnd:
            return None, 0.0

        screenshot_bgr = self.capture_window_screenshot()
        if screenshot_bgr is None:
            return None, 0.0

        return self.match_template_against_image_with_score_adaptive(
            screenshot_bgr=screenshot_bgr,
            template_path=template_path,
            threshold=threshold,
            ignore_text=ignore_text,
            multiscale_enabled=multiscale_enabled,
            multiscale_min=multiscale_min,
            multiscale_max=multiscale_max,
            multiscale_step=multiscale_step,
            mask_regions=mask_regions,
            preprocessing_algorithms=preprocessing_algorithms,
            teaching_window_width=teaching_window_width,
            teaching_window_height=teaching_window_height,
        )

    def match_template_against_image_with_score_adaptive(
        self,
        screenshot_bgr: np.ndarray,
        template_path: str,
        threshold: float = 0.8,
        ignore_text: bool = False,
        multiscale_enabled: bool = True,
        multiscale_min: float = 0.70,
        multiscale_max: float = 1.30,
        multiscale_step: float = 0.05,
        mask_regions: list = None,
        preprocessing_algorithms: list = None,
        teaching_window_width: int = 800,
        teaching_window_height: int = 600,
    ):
        """Match a template against an already loaded BGR image using the same adaptive pipeline as runtime."""
        screenshot_gray = None
        base_mask = None
        working_bgr = None

        try:
            if screenshot_bgr is None:
                return None, 0.0

            working_bgr = screenshot_bgr.copy()

            # Resize screenshot to teaching window size for consistent matching
            original_height, original_width = working_bgr.shape[:2]
            target_width = max(1, int(teaching_window_width) if teaching_window_width else 800)
            target_height = max(1, int(teaching_window_height) if teaching_window_height else 600)
            
            # Calculate scale factors for coordinate mapping
            scale_x = original_width / target_width if target_width > 0 else 1.0
            scale_y = original_height / target_height if target_height > 0 else 1.0
            
            # Log resize information
            teaching_w_str = f"{teaching_window_width}x{teaching_window_height}" if teaching_window_width and teaching_window_height else "N/A"
            self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Current window: {original_width}x{original_height}, Teaching window: {teaching_w_str}, Target: {target_width}x{target_height}")
            if original_width != target_width or original_height != target_height:
                self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Screenshot scale: {scale_x:.3f}x (W), {scale_y:.3f}x (H)")
            
            # Resize screenshot if size differs
            if original_width != target_width or original_height != target_height:
                working_bgr = cv2.resize(working_bgr, (target_width, target_height), interpolation=cv2.INTER_AREA)

            # Apply preprocessing algorithms to screenshot if provided
            if preprocessing_algorithms and len(preprocessing_algorithms) > 0:
                working_bgr = self._apply_preprocessing_algorithms(working_bgr, preprocessing_algorithms)
                self._ui_log(f"<span style='color:blue;'>[Preprocessing]</span> Đã áp dụng {len(preprocessing_algorithms)} thuật toán cho screenshot")

            win_h0, win_w0 = working_bgr.shape[:2]
            base_scale = 1.0
            screenshot_gray = cv2.cvtColor(working_bgr, cv2.COLOR_BGR2GRAY)
            
            # Explicitly delete BGR screenshot after converting to gray (save memory)
            del working_bgr
            working_bgr = None

            win_h = screenshot_gray.shape[0]
            win_w = screenshot_gray.shape[1]
            
            # Load template and apply preprocessing if provided
            template_bgr = _imread_unicode(template_path, cv2.IMREAD_COLOR)
            if template_bgr is None:
                return None, 0.0
            
            template_original_w = template_bgr.shape[1]
            template_original_h = template_bgr.shape[0]
            
            # Resize template based on ratio: target_size / teaching_window_size
            # This ensures template matches the resized screenshot
            template_scale_x = 1.0
            template_scale_y = 1.0
            if teaching_window_width and teaching_window_height:
                try:
                    teaching_w = float(teaching_window_width)
                    teaching_h = float(teaching_window_height)
                    if teaching_w > 0 and teaching_h > 0:
                        template_scale_x = target_width / teaching_w
                        template_scale_y = target_height / teaching_h
                except Exception:
                    pass
            
            # Resize template if scale differs from 1.0
            if abs(template_scale_x - 1.0) > 1e-9 or abs(template_scale_y - 1.0) > 1e-9:
                template_w = max(1, int(template_bgr.shape[1] * template_scale_x))
                template_h = max(1, int(template_bgr.shape[0] * template_scale_y))
                template_bgr = cv2.resize(template_bgr, (template_w, template_h), interpolation=cv2.INTER_AREA)
                self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Template: {template_original_w}x{template_original_h} → {template_w}x{template_h} (scale: {template_scale_x:.3f}x, {template_scale_y:.3f}x)")
            else:
                self._ui_log(f"<span style='color:cyan;'>[Resize]</span> Template: {template_original_w}x{template_original_h} (no resize needed)")
            
            # Apply preprocessing algorithms to template if provided
            if preprocessing_algorithms and len(preprocessing_algorithms) > 0:
                template_bgr = self._apply_preprocessing_algorithms(template_bgr, preprocessing_algorithms)
                self._ui_log(f"<span style='color:blue;'>[Preprocessing]</span> Đã áp dụng {len(preprocessing_algorithms)} thuật toán cho template")
            
            # Convert template to grayscale and cache it
            # NOTE: We need to bypass the cache when using preprocessing because the template changes
            template_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
            
            # Create base mask if mask_regions provided
            if mask_regions and len(mask_regions) > 0:
                base_mask = self._create_mask_array(template_gray, mask_regions)

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
                roi = screenshot_gray[y:y+h, x:x+w]

                # Use template at original scale (no multiscale)
                templ_s = template_gray
                
                if templ_s is None:
                    continue
                if templ_s.shape[0] > roi.shape[0] or templ_s.shape[1] > roi.shape[1]:
                    continue
                
                # Use mask at original scale (no scaling)
                mask_s = base_mask

                # Match with or without mask
                if mask_s is not None:
                    res = cv2.matchTemplate(roi, templ_s, cv2.TM_CCOEFF_NORMED, mask=mask_s)
                else:
                    res = cv2.matchTemplate(roi, templ_s, cv2.TM_CCOEFF_NORMED)
                
                _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(res)
                # Validate and cap score to prevent inf/nan
                max_val = float(max_val)
                if not (0.0 <= max_val <= 1.0):
                    # Invalid score, cap to valid range
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
                # Coordinates are measured on the processed screenshot. Map them
                # back to the original screenshot, including preprocessing scale.
                coord_scale_x = original_width / win_w if win_w > 0 else 1.0
                coord_scale_y = original_height / win_h if win_h > 0 else 1.0
                top_left_x = int(round(best_loc[0] * coord_scale_x))
                top_left_y = int(round(best_loc[1] * coord_scale_y))
                w_orig = int(round(best_wh[0] * coord_scale_x))
                h_orig = int(round(best_wh[1] * coord_scale_y))

                top_left_x = max(0, min(top_left_x, max(0, original_width - 1)))
                top_left_y = max(0, min(top_left_y, max(0, original_height - 1)))
                w_orig = max(1, min(w_orig, original_width - top_left_x))
                h_orig = max(1, min(h_orig, original_height - top_left_y))

                result = (top_left_x, top_left_y, w_orig, h_orig)
                self._last_match[(template_path, bool(ignore_text))] = {
                    "x": int(best_loc[0]),
                    "y": int(best_loc[1]),
                    "w": int(best_wh[0]),
                    "h": int(best_wh[1]),
                }
                self._last_match_stats[(template_path, bool(ignore_text))] = {"rois": used_rois, "win_w": win_w0, "win_h": win_h0}
                return result, max_val

            self._last_match_stats[(template_path, bool(ignore_text))] = {"rois": used_rois, "win_w": win_w0, "win_h": win_h0}
            return None, max_val
            
        finally:
                # CRITICAL: Always cleanup screenshot arrays to prevent memory leaks
                try:
                    if working_bgr is not None:
                        del working_bgr
                        working_bgr = None
                except Exception:
                    pass
                try:
                    if screenshot_gray is not None:
                        del screenshot_gray
                        screenshot_gray = None
                except Exception:
                    pass
                try:
                    if base_mask is not None:
                        del base_mask
                        base_mask = None
                except Exception:
                    pass

    # --- Template Matching Backend (Detector-friendly helper) ---

    def _run_template_matching(
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
    ) -> Optional[DetectionResult]:
        """Core template-matching backend used by non-adaptive API.

        This keeps the legacy behaviour (resize screenshot + template, multiscale
        over template, then map back to original window coords), but wrapped into
        a single helper that returns a DetectionResult for future detectors.
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

        # Resize screenshot if needed for matching space
        if original_width != target_width or original_height != target_height:
            screenshot_bgr = cv2.resize(screenshot_bgr, (target_width, target_height), interpolation=cv2.INTER_AREA)

        screenshot_gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
        template_full = _imread_unicode(template_path, cv2.IMREAD_COLOR)
        if template_full is None:
            return DetectionResult(found=False, score=0.0)

        template_original_w = template_full.shape[1]
        template_original_h = template_full.shape[0]

        # Resize template based on ratio: target_size / teaching_window_size
        template_scale_x = 1.0
        template_scale_y = 1.0
        if teaching_window_width and teaching_window_height:
            try:
                teaching_w = float(teaching_window_width)
                teaching_h = float(teaching_window_height)
                if teaching_w > 0 and teaching_h > 0:
                    template_scale_x = target_width / teaching_w
                    template_scale_y = target_height / teaching_h
            except Exception:
                pass

        if abs(template_scale_x - 1.0) > 1e-9 or abs(template_scale_y - 1.0) > 1e-9:
            template_w = max(1, int(template_full.shape[1] * template_scale_x))
            template_h = max(1, int(template_full.shape[0] * template_scale_y))
            template_full = cv2.resize(template_full, (template_w, template_h), interpolation=cv2.INTER_AREA)
            self._ui_log(
                f"<span style='color:cyan;'>[Resize]</span> Template: {template_original_w}x{template_original_h} → "
                f"{template_w}x{template_h} (scale: {template_scale_x:.3f}x, {template_scale_y:.3f}x)"
            )
        else:
            self._ui_log(
                f"<span style='color:cyan;'>[Resize]</span> Template: {template_original_w}x{template_original_h} (no resize needed)"
            )

        template_gray = cv2.cvtColor(template_full, cv2.COLOR_BGR2GRAY)

        # Multiscale loop (unchanged logic)
        best_val = -1.0
        best_loc = None
        best_scale = 1.0
        best_wh = None

        def _iter_scales():
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
                templ_s = cv2.resize(
                    template_gray,
                    (new_w, new_h),
                    interpolation=cv2.INTER_AREA if s < 1.0 else cv2.INTER_CUBIC,
                )

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
                bbox=(
                    int(best_loc[0] * scale_x),
                    int(best_loc[1] * scale_y),
                    int(best_wh[0] * scale_x),
                    int(best_wh[1] * scale_y),
                ),
                scale=best_scale,
                raw={"scale_x": scale_x, "scale_y": scale_y},
            )

        # Map coordinates back to original window size
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

    # ============ OCR Methods ============
    
    def preprocess_for_ocr(self, img_bgr: np.ndarray, enable_upscale: bool = True, 
                          enable_contrast: bool = True, enable_sharpen: bool = True, 
                          enable_denoise: bool = False, upscale_factor: float = 2.0) -> np.ndarray:
        """Apply OCR preprocessing pipeline."""
        if img_bgr is None:
            return None
        
        preprocessor = self.ocr_preprocessor(img_bgr, self._ui_log)
        
        if enable_upscale:
            preprocessor.upscale(upscale_factor)
        if enable_contrast:
            preprocessor.enhance_contrast()
        if enable_sharpen:
            preprocessor.sharpen()
        if enable_denoise:
            preprocessor.denoise()
        
        return preprocessor.build()
    
    def _ocr_from_bgr(self, bgr_img: np.ndarray, action: AutoAction) -> tuple[str, str]:
        """Run OCR with preprocessing. Returns (text, engine_used)."""
        text = ""
        engine_used = ""
        
        # Check if custom OCR algorithms are provided
        ocr_algorithms = getattr(action, "ocr_algorithms", None)
        
        if ocr_algorithms and len(ocr_algorithms) > 0:
            # Use custom preprocessing algorithms
            bgr_preprocessed = self._apply_preprocessing_algorithms(bgr_img, ocr_algorithms)
            self._ui_log(f"<span style='color:blue;'>[OCR Preprocessing]</span> Đã áp dụng {len(ocr_algorithms)} thuật toán custom")
        else:
            # Use legacy preprocessing (backward compatibility)
            enable_upscale = bool(getattr(action, "ocr_upscale_enabled", True))
            enable_contrast = bool(getattr(action, "ocr_enhance_contrast", True))
            enable_sharpen = bool(getattr(action, "ocr_sharpen", True))
            enable_denoise = bool(getattr(action, "ocr_denoise", False))
            upscale_factor = float(getattr(action, "ocr_upscale_factor", 2.0) or 2.0)
            
            bgr_preprocessed = self.preprocess_for_ocr(
                bgr_img,
                enable_upscale=enable_upscale,
                enable_contrast=enable_contrast,
                enable_sharpen=enable_sharpen,
                enable_denoise=enable_denoise,
                upscale_factor=upscale_factor
            )
        
        try:
            gray = cv2.cvtColor(bgr_preprocessed, cv2.COLOR_BGR2GRAY)
        except Exception:
            gray = None

        ocr_bgr = bgr_preprocessed
        if gray is not None and bool(getattr(action, "ocr_bright_on_dark", False)):
            try:
                k = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
                top = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                top = clahe.apply(top)
                top = cv2.GaussianBlur(top, (3, 3), 0)
                _, thresh = cv2.threshold(top, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                ocr_bgr = cv2.cvtColor(top, cv2.COLOR_GRAY2BGR)
            except Exception:
                thresh = gray if gray is not None else bgr_preprocessed
        else:
            thresh = gray if gray is not None else bgr_preprocessed

        engine_sel = str(getattr(action, "ocr_engine", "auto") or "auto").lower()
        if engine_sel == "paddle":
            engine_sel = "auto"
        if engine_sel not in ("auto", "winrt", "tesseract", "easyocr", "vietocr"):
            engine_sel = "auto"

        # For event_tracking mode, use event_ocr_engine if set
        passive_mode = str(getattr(action, "passive_mode", "") or "")
        if passive_mode == "event_tracking":
            event_engine = str(getattr(action, "event_ocr_engine", "auto") or "auto").lower()
            if event_engine and event_engine != "auto":
                engine_sel = event_engine

        try:
            engine = OCRFactory.create(engine_sel, self._ui_log)
            self._ui_log(f"<span style='color:blue;'>[OCR]</span> Dùng engine: <b>{engine_sel}</b>")
            text = engine.recognize(ocr_bgr)
            engine_used = engine_sel
        except Exception as e:
            self._ui_log(f"<b style='color:red;'>[OCR]</b> Lỗi: {e}")
            text = ""
        
        return text, engine_used
    
    def read_data_from_image(self, image_result: tuple, action: AutoAction, remaining_timeout_s: float | None = None) -> bool:
        """Read data from detected image region."""
        try:
            if len(image_result) >= 4:
                top_left_x, top_left_y, img_w, img_h = image_result[:4]
            else:
                print("[ERROR] image_result không hợp lệ")
                return False
            
            screenshot_bgr = self.capture_window_screenshot()
            if screenshot_bgr is None:
                print("[ERROR] Không thể chụp screenshot để đọc dữ liệu")
                return False
            
            h, w = screenshot_bgr.shape[:2]
            x1 = max(0, top_left_x)
            y1 = max(0, top_left_y)
            x2 = min(w, top_left_x + img_w)
            y2 = min(h, top_left_y + img_h)
            
            if x2 <= x1 or y2 <= y1:
                print("[ERROR] Vùng crop không hợp lệ")
                return False
            
            cropped = screenshot_bgr[y1:y2, x1:x2]
            
            gemini_enabled = bool(getattr(action, "gemini_enabled", False))
            if not gemini_enabled:
                self._ui_log(f"<b style='color:blue;'>[Đọc Dữ Liệu]</b> Đã detect ảnh tại ({top_left_x}, {top_left_y})")
                self._ui_log(f"<b style='color:blue;'>[Đọc Dữ Liệu]</b> Kích thước vùng: {img_w} x {img_h}")

            text, engine_used = self._ocr_from_bgr(cropped, action)

            if not text:
                self._ui_log(
                    "<b style='color:orange;'>[Đọc Dữ Liệu]</b> Không đọc được text (OCR rỗng hoặc không có engine)."
                )
                return False

            if gemini_enabled:
                self._ui_log(
                    "<b>[Text OCR]</b>"
                    f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(text)}</pre>"
                )
                gemini_out = self.gemini_processor.process(text, action, overall_timeout_s=remaining_timeout_s)
                if gemini_out is None:
                    return False
                self._ui_log(
                    "<b>[Gemini]</b>"
                    f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(gemini_out)}</pre>"
                )
                
                if bool(getattr(action, "notification_enabled", False)):
                    self.telegram_notifier.send(action, gemini_out, is_gemini=True)
                
                return True

            self._ui_log(
                "<b>[Text Đọc Được]</b>"
                f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(text)}</pre>"
            )
            
            if bool(getattr(action, "notification_enabled", False)):
                self.telegram_notifier.send(action, text, is_gemini=False)
            return True

        except Exception as e:
            print(f"[ERROR] Lỗi khi đọc dữ liệu từ ảnh: {e}")
            if self.engine and hasattr(self.engine, 'signals'):
                self.engine.signals.log.emit(f"<b style='color:red;'>[Lỗi]</b> Không thể đọc dữ liệu: {str(e)}")
            return False

    def _crop_fixed_roi(self, screenshot_bgr: np.ndarray, action: AutoAction) -> np.ndarray | None:
        if screenshot_bgr is None:
            return None
        h, w = screenshot_bgr.shape[:2]
        roi_x = int(getattr(action, "roi_x", 0) or 0)
        roi_y = int(getattr(action, "roi_y", 0) or 0)
        roi_w = int(getattr(action, "roi_w", 200) or 200)
        roi_h = int(getattr(action, "roi_h", 100) or 100)
        x1 = max(0, min(roi_x, max(0, w - 1)))
        y1 = max(0, min(roi_y, max(0, h - 1)))
        x2 = min(w, x1 + max(1, roi_w))
        y2 = min(h, y1 + max(1, roi_h))
        if x2 <= x1 or y2 <= y1:
            return None
        return screenshot_bgr[y1:y2, x1:x2]

    def _compile_dynamic_ocr_template(self, template: str) -> tuple[re.Pattern[str], list[str]]:
        template = str(template or "").strip()
        placeholders = re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", template)
        if not template:
            raise ValueError("Template rỗng")

        regex_parts: list[str] = []
        last_index = 0
        for match in re.finditer(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", template):
            start, end = match.span()
            literal = template[last_index:start]
            if literal:
                escaped_literal = re.escape(literal).replace(r"\ ", r"\s+")
                regex_parts.append(escaped_literal)
            variable_name = match.group(1)
            regex_parts.append(fr"(?P<{variable_name}>.+?)")
            last_index = end

        tail = template[last_index:]
        if tail:
            regex_parts.append(re.escape(tail).replace(r"\ ", r"\s+"))

        pattern = "^" + "".join(regex_parts) + "$"
        return re.compile(pattern, flags=re.IGNORECASE), placeholders

    def _infer_dynamic_ocr_value(self, raw_value: str):
        raw_value = str(raw_value or "").strip()
        if re.fullmatch(r"-?\d+", raw_value):
            try:
                return int(raw_value)
            except Exception:
                return raw_value
        return raw_value

    def _normalize_dynamic_ocr_match_text(self, text: str) -> str:
        text = str(text or "").lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = re.sub(r"\{[A-Za-z_][A-Za-z0-9_]*\}", " ", text)
        text = re.sub(r"-?\d+", " ", text)
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _dynamic_ocr_fuzzy_score(self, template: str, line: str) -> float:
        template_norm = self._normalize_dynamic_ocr_match_text(template)
        line_norm = self._normalize_dynamic_ocr_match_text(line)
        if not template_norm or not line_norm:
            return 0.0
        return difflib.SequenceMatcher(None, template_norm, line_norm).ratio() * 100.0

    def _extract_dynamic_ocr_values_fuzzy(self, line: str, placeholders: list[str]) -> dict:
        values: dict = {}
        numeric_matches = list(re.finditer(r"-?\d+", str(line or "")))
        for index, variable_name in enumerate(placeholders):
            if index < len(numeric_matches):
                values[variable_name] = self._infer_dynamic_ocr_value(numeric_matches[index].group(0))
            else:
                values[variable_name] = None
        return values

    def _extract_dynamic_ocr_variables(self, text: str, rules: list[dict]) -> dict:
        values: dict = {}
        for rule in list(rules or []):
            variable_name = str(rule.get("variable", "") or "").strip()
            pattern = str(rule.get("pattern", "") or "").strip()
            value_type = str(rule.get("type", "string") or "string").lower()
            if not variable_name or not pattern:
                continue

            value = None
            try:
                match = re.search(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE)
                if match:
                    captured = None
                    if match.lastindex:
                        for idx in range(1, match.lastindex + 1):
                            group_value = match.group(idx)
                            if group_value not in (None, ""):
                                captured = group_value
                                break
                    if captured is None:
                        captured = match.group(0)

                    if value_type == "int":
                        digit_match = re.search(r"-?\d+", str(captured))
                        if digit_match:
                            value = int(digit_match.group(0))
                    else:
                        value = str(captured).strip()
            except Exception:
                value = None

            values[variable_name] = value
        return values

    def _extract_dynamic_ocr_variables_from_patterns(self, text: str, patterns: list[str], threshold: float = 100.0) -> dict:
        values: dict = {}
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        threshold = max(0.0, min(100.0, float(threshold or 100.0)))
        for template in list(patterns or []):
            template = str(template or "").strip()
            if not template:
                continue
            try:
                compiled_regex, placeholders = self._compile_dynamic_ocr_template(template)
            except Exception:
                continue
            matched = False
            for line in lines:
                match = compiled_regex.match(line)
                if not match:
                    continue
                for variable_name in placeholders:
                    if values.get(variable_name) is not None:
                        continue
                    values[variable_name] = self._infer_dynamic_ocr_value(match.group(variable_name))
                matched = True
                break
            if matched:
                continue

            best_line = ""
            best_score = -1.0
            for line in lines:
                score = self._dynamic_ocr_fuzzy_score(template, line)
                if score > best_score:
                    best_score = score
                    best_line = line
            if best_score < threshold:
                continue
            fuzzy_values = self._extract_dynamic_ocr_values_fuzzy(best_line, placeholders)
            if not fuzzy_values or any(value is None for value in fuzzy_values.values()):
                continue
            for variable_name, value in fuzzy_values.items():
                if values.get(variable_name) is None:
                    values[variable_name] = value
        return values

    def _execute_dynamic_ocr_code(self, action: AutoAction, ocr_text: str, extracted_values: dict) -> bool:
        code = str(getattr(action, "dynamic_ocr_code", "return False") or "return False").strip() or "return False"
        lines = [line.strip() for line in str(ocr_text or "").splitlines() if line.strip()]
        safe_globals = {
            "__builtins__": {
                "abs": abs,
                "all": all,
                "any": any,
                "bool": bool,
                "float": float,
                "int": int,
                "len": len,
                "max": max,
                "min": min,
                "range": range,
                "str": str,
                "sum": sum,
            },
            "re": re,
            "ocr_text": str(ocr_text or ""),
            "lines": lines,
        }
        safe_globals.update(dict(extracted_values or {}))
        wrapped_code = "def __dynamic_eval__():\n" + "\n".join(f"    {line}" for line in code.splitlines())
        exec(wrapped_code, safe_globals, safe_globals)
        result = safe_globals["__dynamic_eval__"]()
        if not isinstance(result, bool):
            raise ValueError("Code phải return True hoặc False")
        return result

    def _evaluate_dynamic_ocr_code(self, action: AutoAction, ocr_text: str, extracted_values: dict) -> bool:
        try:
            return self._execute_dynamic_ocr_code(action, ocr_text, extracted_values)
        except Exception as e:
            self._ui_log(f"<b style='color:red;'>[Dynamic OCR]</b> Code lỗi: {e}")
            return False

    def _prepare_bgr_for_ocr(self, bgr_img: np.ndarray, action: AutoAction) -> np.ndarray:
        """Prepare the exact image that will be sent to OCR."""
        ocr_algorithms = getattr(action, "ocr_algorithms", None)

        if ocr_algorithms and len(ocr_algorithms) > 0:
            bgr_preprocessed = self._apply_preprocessing_algorithms(bgr_img, ocr_algorithms)
        else:
            enable_upscale = bool(getattr(action, "ocr_upscale_enabled", True))
            enable_contrast = bool(getattr(action, "ocr_enhance_contrast", True))
            enable_sharpen = bool(getattr(action, "ocr_sharpen", True))
            enable_denoise = bool(getattr(action, "ocr_denoise", False))
            upscale_factor = float(getattr(action, "ocr_upscale_factor", 2.0) or 2.0)

            bgr_preprocessed = self.preprocess_for_ocr(
                bgr_img,
                enable_upscale=enable_upscale,
                enable_contrast=enable_contrast,
                enable_sharpen=enable_sharpen,
                enable_denoise=enable_denoise,
                upscale_factor=upscale_factor
            )

        try:
            gray = cv2.cvtColor(bgr_preprocessed, cv2.COLOR_BGR2GRAY)
        except Exception:
            gray = None

        if gray is not None and bool(getattr(action, "ocr_bright_on_dark", False)):
            try:
                k = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
                top = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                top = clahe.apply(top)
                top = cv2.GaussianBlur(top, (3, 3), 0)
                return cv2.cvtColor(top, cv2.COLOR_GRAY2BGR)
            except Exception:
                pass

        return bgr_preprocessed

    def evaluate_dynamic_ocr_condition_on_image(
        self,
        action: AutoAction,
        screenshot_bgr: np.ndarray,
        include_best_bbox: bool = False,
    ) -> dict:
        """Run Dynamic OCR Condition against a provided screenshot and return detailed diagnostics."""
        diagnostics = {
            "success": False,
            "mode": str(getattr(action, "dynamic_ocr_target_mode", "roi") or "roi").lower(),
            "teaching_match_found": False,
            "teaching_score": 0.0,
            "teaching_bbox": None,
            "target_bgr": None,
            "ocr_preview_bgr": None,
            "ocr_text": "",
            "lines": [],
            "engine_used": "",
            "extracted_values": {},
            "code_result": None,
            "error": "",
        }

        if screenshot_bgr is None:
            diagnostics["error"] = "Khong co anh dau vao"
            return diagnostics

        mode = diagnostics["mode"]
        target_bgr = None

        if mode == "teaching":
            template_path = str(getattr(action, "image_path", "") or "").strip()
            if not template_path or not os.path.exists(template_path):
                diagnostics["error"] = "Chua cau hinh teaching image"
                return diagnostics

            match_threshold = float(getattr(action, "match_threshold", 0.4) or 0.4)
            image_result, score = self.match_template_against_image_with_score_adaptive(
                screenshot_bgr=screenshot_bgr,
                template_path=template_path,
                threshold=0.0 if include_best_bbox else match_threshold,
                multiscale_enabled=bool(getattr(action, "multiscale_enabled", True)),
                mask_regions=getattr(action, "mask_regions", None),
                preprocessing_algorithms=getattr(action, "template_matching_algorithms", None),
                teaching_window_width=getattr(action, "teaching_window_width", None),
                teaching_window_height=getattr(action, "teaching_window_height", None),
            )
            diagnostics["teaching_score"] = float(score or 0.0)
            if image_result is None:
                diagnostics["error"] = "Khong tim thay teaching image"
                return diagnostics

            x, y, w, h = image_result[:4]
            diagnostics["teaching_bbox"] = (int(x), int(y), int(w), int(h))
            diagnostics["teaching_match_found"] = diagnostics["teaching_score"] >= match_threshold
            if not diagnostics["teaching_match_found"]:
                diagnostics["error"] = "Khong tim thay teaching image"
                return diagnostics
            target_bgr = screenshot_bgr[max(0, y):max(0, y) + max(1, h), max(0, x):max(0, x) + max(1, w)]
        else:
            if not bool(getattr(action, "use_fixed_roi", False)):
                diagnostics["error"] = "ROI mode yeu cau bat ROI co dinh"
                return diagnostics
            target_bgr = self._crop_fixed_roi(screenshot_bgr, action)

        if target_bgr is None or getattr(target_bgr, "size", 0) == 0:
            diagnostics["error"] = "Vung OCR khong hop le"
            return diagnostics

        diagnostics["target_bgr"] = target_bgr.copy()
        diagnostics["ocr_preview_bgr"] = self._prepare_bgr_for_ocr(target_bgr, action)

        ocr_text, engine_used = self._ocr_from_bgr(target_bgr, action)
        diagnostics["ocr_text"] = str(ocr_text or "")
        diagnostics["lines"] = [line.strip() for line in diagnostics["ocr_text"].splitlines() if line.strip()]
        diagnostics["engine_used"] = str(engine_used or "")

        if not diagnostics["ocr_text"]:
            diagnostics["error"] = "OCR rong"
            return diagnostics

        patterns = list(getattr(action, "dynamic_ocr_patterns", []) or [])
        if patterns:
            extracted_values = self._extract_dynamic_ocr_variables_from_patterns(
                diagnostics["ocr_text"],
                patterns,
                float(getattr(action, "dynamic_ocr_pattern_threshold", 80.0) or 80.0),
            )
        else:
            extracted_values = self._extract_dynamic_ocr_variables(
                diagnostics["ocr_text"],
                getattr(action, "dynamic_ocr_rules", []) or [],
            )
        diagnostics["extracted_values"] = dict(extracted_values or {})

        try:
            diagnostics["code_result"] = self._execute_dynamic_ocr_code(action, diagnostics["ocr_text"], extracted_values)
        except Exception as e:
            diagnostics["error"] = str(e)
            return diagnostics

        diagnostics["success"] = bool(diagnostics["code_result"])
        return diagnostics

    def _execute_dynamic_ocr_condition(self, action: AutoAction) -> bool:
        screenshot_bgr = self.capture_window_screenshot()
        if screenshot_bgr is None:
            self._ui_log("<b style='color:red;'>[Dynamic OCR]</b> Không thể capture window")
            return False
        diagnostics = self.evaluate_dynamic_ocr_condition_on_image(action, screenshot_bgr)

        if diagnostics["mode"] == "teaching":
            if diagnostics["teaching_match_found"]:
                self._ui_log(
                    f"<b style='color:green;'>[Dynamic OCR]</b> Tìm thấy teaching image "
                    f"(score: {_format_score(diagnostics['teaching_score'])})"
                )
            else:
                self._ui_log(
                    f"<b style='color:red;'>[Dynamic OCR]</b> Không tìm thấy teaching image "
                    f"(score: {_format_score(diagnostics['teaching_score'])})"
                )
                return False

        if diagnostics["error"]:
            self._ui_log(f"<b style='color:red;'>[Dynamic OCR]</b> {diagnostics['error']}")
            return False

        self._ui_log(
            "<b>[Dynamic OCR Text]</b>"
            f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(diagnostics['ocr_text'])}</pre>"
        )
        value_logs = [f"{key}={value!r}" for key, value in diagnostics["extracted_values"].items()]
        self._ui_log(
            f"<b style='color:blue;'>[Dynamic OCR]</b> Engine={diagnostics['engine_used'] or 'unknown'} | "
            f"Values: {', '.join(value_logs) if value_logs else '(none)'}"
        )
        result = bool(diagnostics["code_result"])
        self._ui_log(f"<b style='color:{'green' if result else 'red'};'>[Dynamic OCR]</b> Result: {result}")
        return result

    # ============ Passive Read Methods ============
    
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
    
    def _run_passive_read(self, action: AutoAction, timeout: float | None):
        """Passive read: only OCR/Gemini on new frames, no clicks/detect."""
        passive_mode = str(getattr(action, "passive_mode", "read_data") or "read_data")
        print(f"[DEBUG] _run_passive_read: passive_mode={passive_mode!r}")

        # Use ScreenScanService singleton for all OCR modes
        if passive_mode in ("read_data", "event_tracking", "special_event_tracking"):
            return self._run_passive_read_via_scan_service(action, timeout)

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
            if self.engine and (not self.engine.is_running or self.engine.should_stop_completely):
                self._ui_log("<b style='color:red;'>[Passive]</b> Engine stopped, exiting")
                return False
            if self.engine and bool(getattr(self.engine, "cancel_cycle_requested", False)):
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
            frame = self.capture_window_screenshot()
            if frame is None:
                self._ui_log("<b style='color:red;'>[Passive]</b> Không thể chụp màn hình")
                return False

            roi_frame = frame
            use_fixed_roi = bool(getattr(action, 'use_fixed_roi', False))
            
            self._ui_log(f"<b style='color:blue;'>[Passive Debug]</b> use_fixed_roi = {use_fixed_roi}")
            
            if use_fixed_roi:
                roi_x = int(getattr(action, 'roi_x', 0) or 0)
                roi_y = int(getattr(action, 'roi_y', 0) or 0)
                roi_w = int(getattr(action, 'roi_w', 200) or 200)
                roi_h = int(getattr(action, 'roi_h', 100) or 100)
                
                self._ui_log(f"<b style='color:blue;'>[Passive Debug]</b> ROI coordinates: x={roi_x}, y={roi_y}, w={roi_w}, h={roi_h}")
                
                h, w = frame.shape[:2]
                x1 = max(0, min(roi_x, w-1))
                y1 = max(0, min(roi_y, h-1))
                x2 = min(w, x1 + roi_w)
                y2 = min(h, y1 + roi_h)
                
                if x2 > x1 and y2 > y1:
                    roi_frame = frame[y1:y2, x1:x2]
                    self._ui_log(f"<b style='color:green;'>[Passive]</b> Using fixed ROI at ({x1},{y1}) size {x2-x1}x{y2-y1}")
                else:
                    self._ui_log("<b style='color:orange;'>[Passive]</b> Invalid fixed ROI coordinates, using full frame")
                    
            elif hasattr(action, 'image_path') and action.image_path and os.path.exists(action.image_path):
                self._ui_log(f"<b style='color:blue;'>[Passive]</b> Using teaching image: {os.path.basename(action.image_path)}")
                
                threshold = float(getattr(action, "match_threshold", 0.8))
                ms_enabled = bool(getattr(action, "multiscale_enabled", True))
                mask_regions = getattr(action, "mask_regions", None)
                teaching_window_width = getattr(action, "teaching_window_width", None)
                teaching_window_height = getattr(action, "teaching_window_height", None)
                
                image_result, confidence = self.find_image_in_window_with_score(
                    action.image_path,
                    threshold=threshold,
                    multiscale_enabled=ms_enabled,
                    mask_regions=mask_regions,
                    teaching_window_width=teaching_window_width,
                    teaching_window_height=teaching_window_height,
                )
                
                if image_result and confidence >= threshold:
                    if len(image_result) >= 4:
                        top_left_x, top_left_y, img_w, img_h = image_result[:4]
                        
                        h, w = frame.shape[:2]
                        x1 = max(0, top_left_x)
                        y1 = max(0, top_left_y)
                        x2 = min(w, top_left_x + img_w)
                        y2 = min(h, top_left_y + img_h)
                        
                        if x2 > x1 and y2 > y1:
                            roi_frame = frame[y1:y2, x1:x2]
                            self._ui_log(f"<b style='color:green;'>[Passive]</b> Found ROI at ({x1},{y1}) size {x2-x1}x{y2-y1}, confidence: {confidence:.3f}")
                        else:
                            self._ui_log("<b style='color:orange;'>[Passive]</b> Invalid ROI coordinates, using full frame")
                    else:
                        self._ui_log("<b style='color:orange;'>[Passive]</b> Invalid image_result format, using full frame")
                else:
                    self._ui_log(f"<b style='color:orange;'>[Passive]</b> Teaching image not found (confidence: {confidence:.3f} < {threshold}), using full frame")
            else:
                self._ui_log("<b style='color:gray;'>[Passive]</b> No ROI method specified, using full frame")

            current_hash = self._quick_hash(roi_frame)
            self._ui_log(f"<b style='color:gray;'>[Passive]</b> Frame hash: {current_hash[:8]}...")
            
            if only_new and last_hash and current_hash == last_hash:
                self._ui_log("<b style='color:gray;'>[Passive]</b> Frame giống frame trước, hiển thị kết quả cũ")
                
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

                continue

            self._passive_cache[key] = {"hash": current_hash, "time": now}
            last_hash = current_hash

            self._ui_log("<b style='color:blue;'>[Passive]</b> Frame mới, đang OCR...")
            text, engine_used = self._ocr_from_bgr(roi_frame, action)
            self._ui_log(f"<b style='color:blue;'>[Passive]</b> OCR engine used: {engine_used}")
            
            if not text:
                self._ui_log("<b style='color:orange;'>[Passive]</b> OCR rỗng, bỏ qua frame này")
                continue

            self._ui_log(
                f"<b>[Passive OCR]</b> Text length: {len(text)} chars<br>"
                f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(text)}</pre>"
            )
            
            # Log chi tiết dữ liệu OCR ra console
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Tới mili giây
            print(f"[{timestamp}] [PASSIVE OCR] Engine: {engine_used} | Length: {len(text)} chars")
            print(f"[{timestamp}] [PASSIVE OCR] Data: {text[:200]}..." if len(text) > 200 else f"[{timestamp}] [PASSIVE OCR] Data: {text}")

            gemini_out = None
            if bool(getattr(action, "gemini_enabled", False)):
                self._ui_log("<b style='color:blue;'>[Passive]</b> Gemini enabled, processing...")
                self._ui_log(f"<b style='color:blue;'>[Passive Debug]</b> gemini_enabled={getattr(action, 'gemini_enabled', False)}")
                self._ui_log(f"<b style='color:blue;'>[Passive Debug]</b> prompt={bool(getattr(action, 'prompt', '') or getattr(action, 'gemini_prompt', ''))}")
                gemini_out = self.gemini_processor.process(text, action, overall_timeout_s=30.0)
                if gemini_out:
                    self._ui_log(
                        f"<b>[Passive Gemini]</b> Result length: {len(gemini_out)} chars<br>"
                        f"<pre style='white-space:pre-wrap;word-break:break-word;'>{self._escape_html(gemini_out)}</pre>"
                    )
                else:
                    self._ui_log("<b style='color:orange;'>[Passive Gemini]</b> No result from Gemini")
            else:
                self._ui_log(f"<b style='color:gray;'>[Passive]</b> Gemini disabled (gemini_enabled={getattr(action, 'gemini_enabled', False)})")

            self._passive_cache[key] = {
                "hash": current_hash, 
                "time": now,
                "ocr_text": text,
                "gemini_result": gemini_out or ""
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
                notification_content = gemini_out if gemini_out else text
                if notification_content:
                    # Log OCR data
                    engine_used = "Gemini" if gemini_out else "OCR"
                    self.log_manager.log_ocr_data(notification_content, engine_used)
                    
                    # Filter text based on required keywords
                    required_keywords = str(getattr(action, "notification_filter_keywords", "") or "")
                    matching_sentences = self.text_filter.get_matching_sentences(notification_content, required_keywords)
                    
                    if matching_sentences:
                        # Join matching sentences and send
                        filtered_text = ". ".join(matching_sentences) + "."
                        self._ui_log(f"<b style='color:green;'>[Telegram]</b> Found {len(matching_sentences)} matching sentence(s), sending notification...")
                        self.telegram_notifier.send(action, filtered_text, is_gemini=bool(gemini_out))
                        # Mark as sent to prevent duplicate notifications
                        self.text_filter.mark_sent(notification_content)
                    else:
                        self._ui_log(f"<b style='color:orange;'>[Telegram]</b> No sentences matched filter (missing required keywords)")
                    
                    # Check and perform cleanup if needed
                    cleanup_result = self.log_manager.check_and_cleanup()
                    if cleanup_result is not None:
                        self._ui_log(f"<b style='color:blue;'>[LogManager]</b> Cleanup performed: deleted {cleanup_result} log files")

            self._ui_log(f"<b style='color:green;'>[Passive Success]</b> Processed frame successfully in {time.time()-start:.1f}s")
            
            # Delay theo cài đặt trước khi chụp frame tiếp theo - use interruptible sleep
            if check_interval > 0:
                self._ui_log(f"<b style='color:gray;'>[Passive]</b> Waiting {check_interval}s before next capture...")
                sleep_end = time.time() + check_interval
                while time.time() < sleep_end:
                    if self.engine and (not self.engine.is_running or self.engine.should_stop_completely):
                        self._ui_log("<b style='color:orange;'>[Passive]</b> Engine stopped during sleep")
                        return False
                    time.sleep(0.1)  # Check every 100ms

    # ============ Main Action Execution ============
    
    def _run_passive_detect_image(self, action: AutoAction) -> bool:
        """Passive detect image: wait for template to appear, then proceed to next action.
        
        Mode 2: Phát hiện hình ảnh - sử dụng template matching để chờ ảnh xuất hiện.
        Nếu tìm thấy ảnh → return True (chuyển sang action tiếp theo)
        Nếu timeout → return False
        
        Args:
            action: The READ_PASSIVE action with detect_image mode
            
        Returns:
            True: Image found
            False: Timeout or error
            None: Cancelled
        """
        timeout = float(getattr(action, "passive_detect_timeout", 30.0) or 30.0)
        threshold = float(getattr(action, "passive_detect_threshold", 0.4) or 0.4)
        check_interval = float(getattr(action, "check_interval", 1.0) or 1.0)
        
        # Validate image path or fixed ROI
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
            # Check for cancellation
            if self.engine and (not self.engine.is_running or self.engine.should_stop_completely):
                self._ui_log("<b style='color:orange;'>[Passive Detect]</b> Engine stopped, exiting")
                return None
            
            if self.engine and bool(getattr(self.engine, "cancel_cycle_requested", False)):
                self._ui_log("<b style='color:orange;'>[Passive Detect]</b> Cancel requested")
                return None
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                self._ui_log(f"<b style='color:red;'>[Passive Detect]</b> Timeout ({elapsed:.1f}s > {timeout}s)")
                self._ui_log(f"<b style='color:red;'>[Passive Detect]</b> Best score: {best_score:.3f} < {threshold}")
                return False
            
            check_count += 1
            self._ui_log(f"<b style='color:gray;'>[Passive Detect]</b> Check #{check_count} (elapsed: {elapsed:.1f}s)")
            
            # Try to find image
            if has_image:
                mask_regions = getattr(action, "mask_regions", None)
                teaching_window_width = getattr(action, "teaching_window_width", None)
                teaching_window_height = getattr(action, "teaching_window_height", None)
                image_result, score = self.find_image_in_window_with_score(
                    action.image_path,
                    threshold=threshold,
                    multiscale_enabled=False,  # Không dùng multiscale cho passive detect
                    mask_regions=mask_regions,
                    teaching_window_width=teaching_window_width,
                    teaching_window_height=teaching_window_height,
                )
                
                best_score = max(best_score, score)
                
                if image_result is not None:
                    # Image found!
                    self._ui_log(f"<b style='color:green;'>[Passive Detect]</b> ✓ Tìm thấy ảnh!")
                    self._ui_log(f"<b style='color:green;'>[Passive Detect]</b> Score: {_format_score(score)} >= {threshold}")
                    self._ui_log(f"<b style='color:green;'>[Passive Detect]</b> Elapsed: {elapsed:.1f}s")
                    return True
                else:
                    self._ui_log(f"<b style='color:gray;'>[Passive Detect]</b> Score: {_format_score(score)} < {threshold}")
            
            # Wait before next check - use interruptible sleep
            sleep_end = time.time() + check_interval
            while time.time() < sleep_end:
                if self.engine and (not self.engine.is_running or self.engine.should_stop_completely):
                    self._ui_log("<b style='color:orange;'>[Passive Detect]</b> Engine stopped during sleep")
                    return None
                time.sleep(0.1)  # Check every 100ms
    
    def _run_passive_read_via_scan_service(self, action: AutoAction, timeout: float | None):
        """Run passive read using ScreenScanService singleton for OCR."""
        import threading

        from .screen_scan_service import ScreenScanService, OCRSubscription

        action_id = f"{id(action)}_{getattr(action, 'name', 'unknown')}"

        # Guard: cần hwnd để capture
        if not self.target_window_hwnd:
            self._ui_log("<b style='color:red;'>[Scan OCR]</b> Chưa chọn window target")
            return False

        # Determine ROI
        roi = None
        if bool(getattr(action, "use_fixed_roi", False)):
            roi = (
                int(getattr(action, "roi_x", 0) or 0),
                int(getattr(action, "roi_y", 0) or 0),
                int(getattr(action, "roi_w", 200) or 200),
                int(getattr(action, "roi_h", 100) or 100),
            )

        passive_mode = str(getattr(action, "passive_mode", "read_data") or "read_data")

        # Setup special event subscriptions if needed
        if passive_mode == "special_event_tracking":
            has_special_subscription = self._setup_special_event_subscriptions(action, self.target_window_hwnd)
            if not has_special_subscription:
                self._ui_log("<b style='color:orange;'>[Special Event]</b> No special event subscription was started")
                return False
            try:
                while True:
                    if self.engine and (not self.engine.is_running or self.engine.should_stop_completely):
                        break
                    if self.engine and bool(getattr(self.engine, "cancel_cycle_requested", False)):
                        break
                    time.sleep(0.2)
            finally:
                self._teardown_special_event_subscriptions(action)
            return True

        # Pick correct OCR engine based on mode
        if passive_mode == "event_tracking":
            ocr_engine = str(getattr(action, "event_ocr_engine", "auto") or "auto")
        else:
            ocr_engine = str(getattr(action, "ocr_engine", "auto") or "auto")
        ocr_engine = ocr_engine.lower()
        print(f"[DEBUG] _run_passive_read_via_scan_service: passive_mode={passive_mode!r} ocr_engine={ocr_engine!r}")
        ocr_algorithms = list(getattr(action, "ocr_algorithms", []) or [])

        stop_event = threading.Event()
        result_event = threading.Event()
        matched_event = threading.Event()
        cancelled = False

        event_pattern = str(getattr(action, "event_ocr_pattern", "") or "").strip()
        event_threshold = float(getattr(action, "event_match_threshold", 100.0) or 100.0)
        event_cache = self._passive_cache.setdefault(action_id, {})
        event_reappear_timeout_minutes = int(getattr(action, "event_reappear_timeout_minutes", 15) or 15)
        event_reappear_timeout_s = event_reappear_timeout_minutes * 60

        def on_ocr_result(text: str):
            if stop_event.is_set():
                return
            from datetime import datetime
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{ts}] [ScreenScanService OCR] engine={ocr_engine} roi={roi} text={text[:100]!r}")
            self._ui_log(
                f"<b style='color:green;'>[Scan OCR]</b> engine={ocr_engine} | {self._escape_html(text[:200])}"
            )
            if passive_mode == "event_tracking":
                from .event_tracking_helper import (
                    extract_event_tracking_lines,
                    match_event_tracking_lines,
                    update_event_tracking_state,
                )

                event_lines = extract_event_tracking_lines(text, event_pattern)
                if event_lines:
                    lines_html = "<br>".join(
                        f"[LINE {idx}] {self._escape_html(line)}" for idx, line in enumerate(event_lines)
                    )
                    self._ui_log(f"<b style='color:green;'>[Event Tracking Lines]</b><br>{lines_html}")

                match = match_event_tracking_lines(event_lines, event_pattern, event_threshold)
                if match:
                    now_ts = time.time()
                    resolved = event_pattern
                    vars_str = ", ".join(f"{name}={value}" for name, value in match.get("variables", []))
                    for name, value in match.get("variables", []):
                        resolved = resolved.replace(f"{{{name}}}", value)
                    self._ui_log(
                        f"<b style='color:green;'>[Event Tracking Match]</b> "
                        f"Score: {match['score']:.1f}%<br>"
                        f"<b>→ Dòng:</b> [LINE {int(match.get('line_index', 0))}] {self._escape_html(str(match.get('line', '') or ''))}<br>"
                        f"<b>→ Kết quả:</b> {self._escape_html(resolved)}"
                        + (f"<br><b>Variables:</b> {self._escape_html(vars_str)}" if vars_str else "")
                    )
                    state = update_event_tracking_state(
                        event_cache,
                        resolved,
                        now_ts,
                        event_reappear_timeout_s,
                    )
                    if state["should_pass"]:
                        if state["reason"] == "first_seen":
                            self._ui_log(
                                "<b style='color:green;'>[Event Tracking Match]</b> "
                                "Resolved pattern mới, cho phép chuyển bước."
                            )
                        elif state["reason"] == "reappeared_after_timeout":
                            self._ui_log(
                                "<b style='color:green;'>[Event Tracking Match]</b> "
                                f"Resolved pattern cũ xuất hiện lại sau timeout {event_reappear_timeout_minutes} phút, cho phép chuyển bước."
                            )
                        matched_event.set()
                    else:
                        if state["reason"] == "duplicate_visible":
                            self._ui_log(
                                "<b style='color:orange;'>[Event Tracking Match]</b> "
                                "Resolved pattern trùng với lần đang hiển thị, chưa chuyển bước."
                            )
                        elif state["reason"] == "seen_recently":
                            self._ui_log(
                                "<b style='color:orange;'>[Event Tracking Match]</b> "
                                f"Resolved pattern đã thấy gần đây và chưa quá timeout {event_reappear_timeout_minutes} phút."
                            )
                else:
                    had_visible_pattern = bool(event_cache.get("current_visible_pattern"))
                    state = update_event_tracking_state(
                        event_cache,
                        None,
                        time.time(),
                        event_reappear_timeout_s,
                    )
                    if state["reason"] == "no_match" and had_visible_pattern:
                        self._ui_log(
                            "<b style='color:gray;'>[Event Tracking Match]</b> "
                            f"Resolved pattern không còn xuất hiện, bắt đầu tính timeout {event_reappear_timeout_minutes} phút."
                        )
            result_event.set()

        sub = OCRSubscription(
            action_id=action_id,
            hwnd=self.target_window_hwnd,
            roi=roi,
            ocr_engine=ocr_engine,
            ocr_algorithms=ocr_algorithms,
            callback=on_ocr_result,
        )

        self._ui_log(f"<b style='color:blue;'>[Scan OCR]</b> Subscribing action {action.name} roi={roi} engine={ocr_engine}")
        service = ScreenScanService.get_instance()
        service.subscribe(sub)

        try:
            # Run until engine stops - check every 200ms, không block lâu
            while True:
                if matched_event.is_set():
                    return True
                if self.engine and (not self.engine.is_running or self.engine.should_stop_completely):
                    cancelled = True
                    break
                if self.engine and bool(getattr(self.engine, "cancel_cycle_requested", False)):
                    cancelled = True
                    break
                result_event.wait(timeout=0.2)
                result_event.clear()
        finally:
            stop_event.set()
            result_event.set()  # Unblock jika sedang wait
            service.unsubscribe(action_id)
            self._ui_log(f"<b style='color:gray;'>[Scan OCR]</b> Unsubscribed {action.name}")

        return None if cancelled else False

    def _send_key_with_sendinput(self, key_str: str) -> bool:
        """Send keyboard input using SendInput API (bypasses BlockInput from same process).
        
        Args:
            key_str: Key string (e.g., 'a', 'ctrl+c', 'f1')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import ctypes
            from ctypes import wintypes
            
            # Define SendInput structures
            # IMPORTANT: INPUT must match the WinAPI layout/size, otherwise SendInput
            # fails with ERROR_INVALID_PARAMETER (87).
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                ULONG_PTR = ctypes.c_ulonglong
            else:
                ULONG_PTR = ctypes.c_ulong

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR),
                ]

            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ("wVk", wintypes.WORD),
                    ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR),
                ]

            class HARDWAREINPUT(ctypes.Structure):
                _fields_ = [
                    ("uMsg", wintypes.DWORD),
                    ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD),
                ]
            
            class INPUT(ctypes.Structure):
                class _INPUT_UNION(ctypes.Union):
                    _fields_ = [
                        ("mi", MOUSEINPUT),
                        ("ki", KEYBDINPUT),
                        ("hi", HARDWAREINPUT),
                    ]
                _anonymous_ = ("_input",)
                _fields_ = [
                    ("type", wintypes.DWORD),
                    ("_input", _INPUT_UNION),
                ]
            
            INPUT_KEYBOARD = 1
            KEYEVENTF_KEYUP = 0x0002
            KEYEVENTF_UNICODE = 0x0004
            KEYEVENTF_SCANCODE = 0x0008
            KEYEVENTF_EXTENDEDKEY = 0x0001

            VK_SHIFT = 0x10
            VK_CONTROL = 0x11
            VK_MENU = 0x12  # ALT
            
            # Tool marker (ULONG_PTR)
            TOOL_MARKER = 0xAB10
            extra_info = ULONG_PTR(TOOL_MARKER)

            # NOTE:
            # Do NOT set ctypes function argtypes/restype on windll.user32.SendInput here.
            # It is global and can break other modules that define their own INPUT layout
            # (e.g., mouse_controller.py), causing TypeError at runtime.
            SendInput = ctypes.windll.user32.SendInput

            normalized_key = str(key_str or "").strip().lower()
            special_vk_map = {
                "tab": 0x09,
                "esc": 0x1B,
                "escape": 0x1B,
                "enter": 0x0D,
                "return": 0x0D,
                "space": 0x20,
                "backspace": 0x08,
                "delete": 0x2E,
                "del": 0x2E,
                "insert": 0x2D,
                "ins": 0x2D,
                "home": 0x24,
                "end": 0x23,
                "page up": 0x21,
                "pageup": 0x21,
                "page down": 0x22,
                "pagedown": 0x22,
                "up": 0x26,
                "down": 0x28,
                "left": 0x25,
                "right": 0x27,
                "caps lock": 0x14,
                "capslock": 0x14,
                "num lock": 0x90,
                "numlock": 0x90,
                "scroll lock": 0x91,
                "scrolllock": 0x91,
                "print screen": 0x2C,
                "printscreen": 0x2C,
                "pause": 0x13,
                "menu": 0x5D,
                "windows": 0x5B,
                "win": 0x5B,
            }
            for i in range(1, 13):
                special_vk_map[f"f{i}"] = 0x6F + i
            extended_vk_codes = {
                0x2D, 0x2E, 0x24, 0x23, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28, 0x5B, 0x5D,
            }
            
            # Parse key string (simple implementation, only supports single keys for now)
            # For complex keys like 'ctrl+c', fallback to keyboard library
            if '+' in key_str:
                # Fallback to keyboard library for complex keys
                import keyboard
                keyboard.press_and_release(key_str)
                return True

            shift_state = 0
            vk_code = special_vk_map.get(normalized_key)
            use_unicode_fallback = False
            if vk_code is None:
                if len(key_str) != 1:
                    import keyboard
                    keyboard.press_and_release(key_str)
                    return True
                vk = ctypes.windll.user32.VkKeyScanW(ord(key_str))
                if vk == -1:
                    use_unicode_fallback = True
                    vk_code = 0
                else:
                    vk_code = vk & 0xFF
                    shift_state = (vk >> 8) & 0xFF  # 1=SHIFT, 2=CTRL, 4=ALT

            # Prefer scan-code injection (more compatible with games/raw input than VK-only)
            MapVirtualKeyW = ctypes.windll.user32.MapVirtualKeyW
            MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
            MapVirtualKeyW.restype = wintypes.UINT

            def _mk_key_input(vk_c: int, is_up: bool) -> INPUT:
                sc = int(MapVirtualKeyW(vk_c, 0)) & 0xFF
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki.wVk = 0  # using scan code
                inp.ki.wScan = sc
                flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if is_up else 0)
                if vk_c in extended_vk_codes:
                    flags |= KEYEVENTF_EXTENDEDKEY
                inp.ki.dwFlags = flags
                inp.ki.time = 0
                inp.ki.dwExtraInfo = TOOL_MARKER  # Use integer directly
                return inp

            def _mk_unicode_input(ch: str, is_up: bool) -> INPUT:
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki.wVk = 0
                inp.ki.wScan = ord(ch)
                inp.ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if is_up else 0)
                inp.ki.time = 0
                inp.ki.dwExtraInfo = TOOL_MARKER  # Use integer directly
                return inp

            # Build input sequence: modifiers down -> key down/up -> modifiers up
            seq: list[INPUT] = []
            mods: list[int] = []
            if shift_state & 1:
                mods.append(VK_SHIFT)
            if shift_state & 2:
                mods.append(VK_CONTROL)
            if shift_state & 4:
                mods.append(VK_MENU)

            for m in mods:
                seq.append(_mk_key_input(m, is_up=False))

            # Main key (scan code; fallback to UNICODE if scan code is 0)
            if not use_unicode_fallback and int(MapVirtualKeyW(vk_code, 0)) & 0xFF:
                seq.append(_mk_key_input(vk_code, is_up=False))
                seq.append(_mk_key_input(vk_code, is_up=True))
            else:
                # Extremely rare, but keep a fallback for layout edge cases
                seq.append(_mk_unicode_input(key_str, is_up=False))
                seq.append(_mk_unicode_input(key_str, is_up=True))

            for m in reversed(mods):
                seq.append(_mk_key_input(m, is_up=True))

            inputs = (INPUT * len(seq))(*seq)
            expected = len(seq)
            p_inputs = ctypes.cast(inputs, ctypes.POINTER(INPUT))
            result = SendInput(expected, p_inputs, ctypes.sizeof(INPUT))

            if result != expected:
                last_error = ctypes.windll.kernel32.GetLastError()
                print(
                    f"[KEY DEBUG] SendInput returned {result}/{expected}, last_error={last_error}, "
                    f"vk={vk_code}, shift_state={shift_state}, cbSize={ctypes.sizeof(INPUT)}"
                )

            return result == expected
            
        except Exception as e:
            self._ui_log(f"<b style='color:orange;'>[Key]</b> SendInput failed, fallback to keyboard: {e}")
            # Fallback to keyboard library
            try:
                import keyboard
                keyboard.press_and_release(key_str)
                return True
            except Exception as e2:
                self._ui_log(f"<b style='color:red;'>[Key]</b> Keyboard fallback failed: {e2}")
                return False
        finally:
            self.release_all_modifier_keys()
    
    def execute(self, action: AutoAction) -> bool:
        """Execute action based on type."""
        import traceback
        try:
            # Wrap entire execute function to catch any unhandled exceptions
            return self._execute_internal(action)
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"[SystemExecutor.execute] FATAL ERROR: {error_msg}")
            print(f"[SystemExecutor.execute] TRACEBACK:\n{error_trace}")
            try:
                self._ui_log(f"<b style='color:red;'>[Execute]</b> ❌ Lỗi nghiêm trọng: {error_msg}")
                self._ui_log(f"<pre style='color:red;font-size:10px;'>{self._escape_html(error_trace)}</pre>")
            except Exception:
                # Even logging failed, just print
                pass
            return False
    
    def _sleep_interruptible(self, seconds: float) -> bool:
        """Sleep in short intervals so stop flags can interrupt long waits."""
        end_time = time.time() + max(0.0, float(seconds or 0.0))
        while time.time() < end_time:
            if self.engine and (not self.engine.is_running or self.engine.should_stop_completely):
                return False
            if self.engine and bool(getattr(self.engine, "cancel_cycle_requested", False)):
                return False
            time.sleep(min(0.1, max(0.0, end_time - time.time())))
        return True

    def _apply_action_delay(self, action: AutoAction) -> bool:
        """Apply post-action delay in 100ms chunks, interruptible by stop/cancel."""
        delay = float(getattr(action, "delay", 0.0) or 0.0)
        if delay <= 0:
            return True
        self._ui_log(f"<span style='color:gray;'>[Delay]</span> Chờ {delay:.2f}s")
        if not self._sleep_interruptible(delay):
            self._ui_log("<b style='color:orange;'>[Delay]</b> Bị dừng trong lúc delay")
            return False
        return True

    def _detect_teaching_image_once(self, action: AutoAction):
        """Run one teaching-image detection pass for actions that reuse template matching."""
        image_path = getattr(action, "image_path", None)
        if not image_path or not os.path.exists(image_path):
            return None, 0.0
        threshold = float(getattr(action, "match_threshold", 0.4) or 0.4)
        teaching_window_width = getattr(action, "teaching_window_width", None) or 800
        teaching_window_height = getattr(action, "teaching_window_height", None) or 600
        return self.find_image_in_window_with_score(
            image_path,
            threshold=threshold,
            multiscale_enabled=False,
            teaching_window_width=teaching_window_width,
            teaching_window_height=teaching_window_height,
        )

    def _detect_post_click_image_once(self, action: AutoAction):
        """Run one expected-result image detection pass after a mouse click."""
        image_path = getattr(action, "post_click_image_path", None)
        if not image_path or not os.path.exists(image_path):
            return None, 0.0
        threshold = float(getattr(action, "post_click_match_threshold", 0.4) or 0.4)
        teaching_window_width = getattr(action, "post_click_teaching_window_width", None) or 800
        teaching_window_height = getattr(action, "post_click_teaching_window_height", None) or 600
        return self.find_image_in_window_with_score(
            image_path,
            threshold=threshold,
            multiscale_enabled=False,
            teaching_window_width=teaching_window_width,
            teaching_window_height=teaching_window_height,
        )

    def _perform_coordinate_mouse_click(self, action: AutoAction) -> bool:
        """Perform one coordinate-based mouse click."""
        coord_pos = getattr(action, "coordinate_click_pos", None)
        if not coord_pos or len(coord_pos) < 2:
            self._ui_log("<b style='color:red;'>[Click]</b> Thất bại: chưa cấu hình tọa độ click")
            return False

        client_x = int(coord_pos[0])
        client_y = int(coord_pos[1])
        self._ui_log(f"<b>[Click]</b> Chế độ tọa độ: click tại ({client_x}, {client_y})")

        if not self.target_window_hwnd:
            self._ui_log("<b style='color:red;'>[Click]</b> Thất bại: không có target window")
            return False

        try:
            import win32gui

            client_rect = win32gui.GetClientRect(self.target_window_hwnd)
            client_w = client_rect[2] - client_rect[0]
            client_h = client_rect[3] - client_rect[1]

            if client_x < 0 or client_y < 0 or client_x >= client_w or client_y >= client_h:
                self._ui_log(
                    f"<b style='color:red;'>[Click]</b> Bỏ qua: tọa độ ({client_x},{client_y}) nằm ngoài client area ({client_w}x{client_h})"
                )
                return False

            client_origin = win32gui.ClientToScreen(self.target_window_hwnd, (0, 0))
            screen_x = client_origin[0] + client_x
            screen_y = client_origin[1] + client_y

            self._ui_log(f"<span style='color:gray;'>[Debug] Screen click pos: ({screen_x},{screen_y})</span>")

            use_alt = bool(getattr(action, "alt_click", False))
            self._set_tool_acting(True)
            self.mouse_controller.click_with_optional_alt(screen_x, screen_y, client_x, client_y, use_alt)
            self._set_tool_acting(False)
            return True
        except Exception as e:
            self._set_tool_acting(False)
            self._ui_log(f"<b style='color:red;'>[Click]</b> Lỗi: {e}")
            return False

    def _perform_template_mouse_click(self, action: AutoAction) -> bool:
        """Perform one template-matching mouse click."""
        if not action.image_path or not os.path.exists(action.image_path):
            self._ui_log("<b style='color:red;'>[Click]</b> Thất bại: chưa cấu hình ảnh template")
            return False

        self._ui_log(f"<b>[Click]</b> Tìm ảnh: {os.path.basename(action.image_path)}")
        threshold = float(getattr(action, "match_threshold", 0.8) or 0.8)
        mask_regions = getattr(action, "mask_regions", None)
        teaching_window_width = getattr(action, "teaching_window_width", None)
        teaching_window_height = getattr(action, "teaching_window_height", None)
        preprocessing_algorithms = getattr(action, "template_matching_algorithms", None)

        image_result, score = self.find_image_in_window_with_score(
            action.image_path,
            threshold=threshold,
            multiscale_enabled=bool(getattr(action, "multiscale_enabled", True)),
            mask_regions=mask_regions,
            teaching_window_width=teaching_window_width,
            teaching_window_height=teaching_window_height,
            preprocessing_algorithms=preprocessing_algorithms
        )

        if image_result is None:
            self._ui_log(f"<b style='color:red;'>[Click]</b> Không tìm thấy ảnh (score: {_format_score(score)} < {threshold})")
            return False

        self._ui_log(f"<b style='color:green;'>[Click]</b> Tìm thấy ảnh (score: {_format_score(score)})")

        click_x = int(getattr(action, "click_x", 0) or 0)
        click_y = int(getattr(action, "click_y", 0) or 0)
        screen_x, screen_y, client_x, client_y = self.calculate_click_position(image_result, click_x, click_y)

        self._ui_log(f"<b>[Click]</b> Click tại ({screen_x}, {screen_y})")
        use_alt = bool(getattr(action, "alt_click", False))
        self._set_tool_acting(True)
        self.mouse_controller.click_with_optional_alt(screen_x, screen_y, client_x, client_y, use_alt)
        self._set_tool_acting(False)
        return True

    def _execute_mouse_click_with_post_check(self, action: AutoAction) -> bool:
        """After a successful mouse click, wait and verify the expected result image appears."""
        if not getattr(action, "post_click_image_path", None) or not os.path.exists(str(getattr(action, "post_click_image_path", "") or "")):
            self._ui_log("<b style='color:red;'>[Click]</b> Bật check ảnh sau click nhưng chưa cấu hình ảnh kết quả")
            return False

        retry_count = max(0, int(getattr(action, "post_click_retry_count", 0) or 0))
        check_delay = max(0.0, float(getattr(action, "post_click_check_delay", 1.0) or 0.0))
        threshold = float(getattr(action, "post_click_match_threshold", 0.4) or 0.4)
        total_attempts = retry_count + 1
        click_by_coordinate = bool(getattr(action, "click_by_coordinate", False))

        for attempt_index in range(total_attempts):
            if attempt_index > 0:
                self._ui_log(
                    f"<b style='color:orange;'>[Click]</b> Retry {attempt_index}/{retry_count}: click lại và kiểm tra ảnh kết quả"
                )
                if click_by_coordinate:
                    if not self._perform_coordinate_mouse_click(action):
                        return False
                else:
                    if not self._perform_template_mouse_click(action):
                        return False

            self._ui_log(
                f"<span style='color:gray;'>[Click]</span> Chờ {check_delay:.1f}s trước khi check ảnh kết quả"
            )
            if not self._sleep_interruptible(check_delay):
                self._ui_log("<b style='color:orange;'>[Click]</b> Bị dừng trong lúc chờ check ảnh kết quả")
                return False

            image_result, score = self._detect_post_click_image_once(action)
            if image_result and score >= threshold:
                self._ui_log(
                    f"<b style='color:green;'>[Click]</b> Ảnh kết quả đã xuất hiện (score: {_format_score(score)} >= {threshold:.2f})"
                )
                return True

            self._ui_log(
                f"<b style='color:orange;'>[Click]</b> Chưa thấy ảnh kết quả sau lần {attempt_index + 1}/{total_attempts} "
                f"(score: {_format_score(score)} < {threshold:.2f})"
            )

        self._ui_log("<b style='color:red;'>[Click]</b> Hết số lần retry mà ảnh kết quả vẫn chưa xuất hiện")
        return False

    def _execute_keyboard_with_post_check(self, action: AutoAction, key_str: str) -> bool:
        """Press a key, wait, then verify the configured teaching image appears."""
        if not getattr(action, "image_path", None) or not os.path.exists(str(getattr(action, "image_path", "") or "")):
            self._ui_log("<b style='color:red;'>[Key]</b> Bật check ảnh nhưng chưa cấu hình teaching image")
            return False

        retry_count = max(0, int(getattr(action, "post_key_retry_count", 0) or 0))
        check_delay = max(0.0, float(getattr(action, "post_key_check_delay", 1.0) or 0.0))
        threshold = float(getattr(action, "match_threshold", 0.4) or 0.4)
        total_attempts = retry_count + 1

        for attempt_index in range(total_attempts):
            if attempt_index > 0:
                self._ui_log(
                    f"<b style='color:orange;'>[Key]</b> Retry {attempt_index}/{retry_count}: press lại <code>{key_str}</code>"
                )
                self._set_tool_acting(True)
                success = self._send_key_with_sendinput(key_str)
                self._set_tool_acting(False)
                if not success:
                    self._ui_log(f"<b style='color:red;'>[Key]</b> Retry {attempt_index} thất bại khi gửi phím")
                    return False

            self._ui_log(
                f"<span style='color:gray;'>[Key]</span> Chờ {check_delay:.1f}s trước khi check teaching image"
            )
            if not self._sleep_interruptible(check_delay):
                self._ui_log("<b style='color:orange;'>[Key]</b> Bị dừng trong lúc chờ check teaching image")
                return False

            image_result, score = self._detect_teaching_image_once(action)
            if image_result and score >= threshold:
                self._ui_log(
                    f"<b style='color:green;'>[Key]</b> Teaching image xuất hiện (score: {_format_score(score)} >= {threshold:.2f})"
                )
                return True

            self._ui_log(
                f"<b style='color:orange;'>[Key]</b> Chưa thấy teaching image sau lần {attempt_index + 1}/{total_attempts} "
                f"(score: {_format_score(score)} < {threshold:.2f})"
            )

        self._ui_log("<b style='color:red;'>[Key]</b> Hết số lần retry mà teaching image vẫn chưa xuất hiện")
        return False

    def _execute_internal(self, action: AutoAction) -> bool:
        """Internal execute method (actual implementation)."""
        if action.action_type == ActionType.KEYBOARD:
            # Focus window TRƯỚC KHI block input (focus cần input không bị block)
            focus_success = self._focus_target_window()
            if not focus_success:
                self._ui_log("<b style='color:red;'>[Key]</b> Thất bại: không thể focus window")
                return False
            
            if not action.value or not str(action.value).strip():
                self._ui_log("<b style='color:red;'>[Key]</b> Thất bại: chưa cấu hình phím (action.value rỗng)")
                print(f"[KEY DEBUG] FAIL: empty key | hwnd={self.target_window_hwnd}")
                return False

            key_str = str(action.value).strip()
            print(f"[KEY DEBUG] START | hwnd={self.target_window_hwnd} | key={key_str!r} | len={len(key_str)}")
            self._ui_log(f"<b>[Key]</b> Press: <code>{key_str}</code>")
            if self.target_window_hwnd:
                try:
                    self._set_tool_acting(True)
                    # Use SendInput instead of keyboard library (bypasses BlockInput)
                    success = self._send_key_with_sendinput(key_str)
                    self._set_tool_acting(False)
                    if success:
                        self._ui_log(f"<b style='color:green;'>[Key]</b> Success: {key_str}")
                        if bool(getattr(action, "enable_post_key_image_check", False)):
                            return self._execute_keyboard_with_post_check(action, key_str)
                        return True
                    else:
                        self._ui_log(f"<b style='color:red;'>[Key]</b> Failed to send key")
                        return False
                except Exception as e:
                    self._set_tool_acting(False)
                    self._ui_log(f"<b style='color:red;'>[Key]</b> Lỗi: {e}")
                    return False
            return False

        elif action.action_type == ActionType.MOUSE_CLICK:
            # Track memory usage before click
            memory_before = self.get_memory_usage_mb()
            click_success = False
            screenshot_gray = None
            image_result = None
            
            try:
                # Focus window TRƯỚC KHI block input
                focus_success = self._focus_target_window()
                if not focus_success:
                    self._ui_log("<b style='color:red;'>[Click]</b> Thất bại: không thể focus window")
                    return False
                
                # Check if coordinate mode
                click_by_coordinate = bool(getattr(action, "click_by_coordinate", False))
                
                if click_by_coordinate:
                    click_success = self._perform_coordinate_mouse_click(action)
                    if not click_success:
                        return False
                    if bool(getattr(action, "enable_post_click_image_check", False)):
                        return self._execute_mouse_click_with_post_check(action)
                    return True
                else:
                    click_success = self._perform_template_mouse_click(action)
                    if not click_success:
                        return False
                    if bool(getattr(action, "enable_post_click_image_check", False)):
                        return self._execute_mouse_click_with_post_check(action)
                    return True
            finally:
                # Explicit memory cleanup - set references to None
                try:
                    if screenshot_gray is not None:
                        del screenshot_gray
                        screenshot_gray = None
                    if image_result is not None:
                        del image_result
                        image_result = None
                except Exception:
                    pass
                
                # SAFE: Only cleanup memory AFTER click completes successfully
                # Do NOT clear cache in finally - it can crash if cache is being used
                if click_success:
                    try:
                        # Clear all caches and force garbage collection
                        self.clear_all_caches()
                        
                        # Track memory usage after cleanup
                        memory_after = self.get_memory_usage_mb()
                        memory_diff = memory_after - memory_before
                        
                        if memory_diff > 5.0:  # Log if memory increased by more than 5MB
                            self._ui_log(f"<b style='color:orange;'>[Memory]</b> Usage: {memory_before:.1f}MB → {memory_after:.1f}MB (+{memory_diff:.1f}MB)")
                        else:
                            self._ui_log(f"<b style='color:gray;'>[Memory]</b> Usage: {memory_after:.1f}MB")
                            
                    except Exception as cleanup_error:
                        self._ui_log(f"<b style='color:orange;'>[Memory]</b> Cleanup error: {cleanup_error}")

        elif action.action_type == ActionType.EVENT_NOTIFY:
            # Gate by event preparation window(s). If outside, return False (timeout)
            try:
                import time as _time
                import traceback
                from datetime import datetime, timedelta

                # Get action attributes
                try:
                    event_name = str(getattr(action, "name", "") or "").strip() or "Thông báo sự kiện"
                    times_raw = list(getattr(action, "event_notify_times", []) or [])
                    prepare_start_s = int(getattr(action, "event_prepare_start_s", 300) or 300)
                    prepare_end_s = int(getattr(action, "event_prepare_end_s", 60) or 60)
                    
                    # Filter only enabled times and extract time strings
                    times = []
                    for t in times_raw:
                        if isinstance(t, dict):
                            # New format: {"time": "10:58", "enabled": true}
                            if t.get("enabled", True):  # Default enabled if missing
                                times.append(t.get("time", ""))
                        else:
                            # Old format: "10:58" (always enabled)
                            times.append(str(t))
                    
                    print(f"[EventNotify DEBUG] Raw times: {times_raw}")
                    print(f"[EventNotify DEBUG] Filtered enabled times: {times}")
                    
                except Exception as e1:
                    print(f"[EventNotify] ERROR reading config: {e1}")
                    print(traceback.format_exc())
                    self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi đọc cấu hình: {e1}")
                    return False

                # Validate config
                try:
                    if not times:
                        self._ui_log(
                            "<b style='color:red;'>[Event]</b> ❌ Thất bại: không có mốc thời gian nào được enable. "
                            "Vui lòng mở cài đặt action và enable ít nhất 1 mốc thời gian bằng cách check checkbox."
                        )
                        return False
                    if prepare_start_s <= prepare_end_s or prepare_start_s < 0 or prepare_end_s < 0:
                        self._ui_log(
                            "<b style='color:red;'>[Event]</b> Thất bại: cấu hình sai "
                            f"(start={prepare_start_s}s phải > end={prepare_end_s}s)"
                        )
                        return False
                except Exception as e2:
                    print(f"[EventNotify] ERROR validating config: {e2}")
                    print(traceback.format_exc())
                    self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi validate: {e2}")
                    return False

                # Get current time
                try:
                    now_ts = int(_time.time())
                    now_dt = datetime.fromtimestamp(now_ts)
                except Exception as e3:
                    print(f"[EventNotify] ERROR getting time: {e3}")
                    print(traceback.format_exc())
                    self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi lấy thời gian: {e3}")
                    return False

                # Log check info
                try:
                    self._ui_log(
                        f"<b>[Event]</b> Check: <code>{self._escape_html(event_name)}</code> | "
                        f"mốc={len(times)} | window={prepare_start_s}s→{prepare_end_s}s | "
                        f"now={now_dt.strftime('%H:%M:%S')}"
                    )
                except Exception as e4:
                    print(f"[EventNotify] ERROR logging check info: {e4}")
                    print(traceback.format_exc())
                    # Continue even if log fails

                # Evaluate windows
                try:
                    matched = None  # (event_ts, start_ts, end_ts, label)
                    next_window_start = None  # earliest start_ts after now

                    for idx, t in enumerate(times):
                        try:
                            t = str(t or "").strip()
                            if not t:
                                continue
                            
                            # Parse HH:MM
                            try:
                                hh_str, mm_str = t.split(":")
                                hh = int(hh_str)
                                mm = int(mm_str)
                                if hh < 0 or hh > 23 or mm < 0 or mm > 59:
                                    continue
                            except Exception as parse_err:
                                print(f"[EventNotify] ERROR parsing time[{idx}] '{t}': {parse_err}")
                                continue

                            # Calculate windows for today and tomorrow
                            try:
                                base_today = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
                                
                                for day_offset in (0, 1):
                                    try:
                                        event_dt = base_today + timedelta(days=day_offset)
                                        event_ts = int(event_dt.timestamp())
                                        start_ts = event_ts - prepare_start_s
                                        end_ts = event_ts - prepare_end_s
                                        
                                        # Debug log
                                        start_dt_dbg = datetime.fromtimestamp(start_ts)
                                        end_dt_dbg = datetime.fromtimestamp(end_ts)
                                        print(f"[EventNotify DEBUG] Event {t} (day+{day_offset}): window {start_dt_dbg.strftime('%H:%M:%S')} - {end_dt_dbg.strftime('%H:%M:%S')}, now_ts={now_ts}, start_ts={start_ts}, end_ts={end_ts}")
                                        print(f"[EventNotify DEBUG] Check: {start_ts} <= {now_ts} <= {end_ts} = {start_ts <= now_ts <= end_ts}")

                                        if start_ts <= now_ts <= end_ts:
                                            matched = (event_ts, start_ts, end_ts, t)
                                            break

                                        if now_ts < start_ts:
                                            if next_window_start is None or start_ts < next_window_start:
                                                next_window_start = start_ts
                                    except Exception as day_err:
                                        print(f"[EventNotify] ERROR calculating day_offset={day_offset} for time[{idx}] '{t}': {day_err}")
                                        print(traceback.format_exc())
                                        continue

                                if matched:
                                    break
                            except Exception as calc_err:
                                print(f"[EventNotify] ERROR calculating windows for time[{idx}] '{t}': {calc_err}")
                                print(traceback.format_exc())
                                continue
                        except Exception as time_err:
                            print(f"[EventNotify] ERROR processing time[{idx}]: {time_err}")
                            print(traceback.format_exc())
                            continue
                except Exception as e5:
                    print(f"[EventNotify] ERROR evaluating windows: {e5}")
                    print(traceback.format_exc())
                    self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi tính toán cửa sổ: {e5}")
                    return False

                # Handle result
                try:
                    result = None
                    if matched:
                        event_ts, start_ts, end_ts, label = matched
                        start_dt = datetime.fromtimestamp(start_ts)
                        end_dt = datetime.fromtimestamp(end_ts)
                        event_dt = datetime.fromtimestamp(event_ts)
                        self._ui_log(
                            f"<b style='color:green;'>[Event]</b> ✓ Trong khoảng cho phép: "
                            f"<code>{start_dt.strftime('%H:%M:%S')}</code> - <code>{end_dt.strftime('%H:%M:%S')}</code> "
                            f"(mốc <code>{label}</code>, event <code>{event_dt.strftime('%H:%M')}</code>)"
                        )
                        result = True
                    else:
                        # Not matched → timeout
                        if next_window_start is not None:
                            nxt = datetime.fromtimestamp(int(next_window_start))
                            now_dt_str = now_dt.strftime('%H:%M:%S')
                            nxt_str = nxt.strftime('%H:%M:%S')
                            self._ui_log(
                                f"<b style='color:red;'>[Event]</b> ✗ Ngoài khoảng cho phép → Timeout<br>"
                                f"<span style='color:gray;'>Hiện tại: <code>{now_dt_str}</code> | "
                                f"Cửa sổ kế tiếp bắt đầu: <code>{nxt_str}</code></span>"
                            )
                        else:
                            # All windows are in the past (no future windows)
                            self._ui_log(
                                f"<b style='color:red;'>[Event]</b> ✗ Ngoài khoảng cho phép → Timeout<br>"
                                f"<span style='color:gray;'>Hiện tại: <code>{now_dt.strftime('%H:%M:%S')}</code> | "
                                f"Đã qua tất cả cửa sổ trong ngày. Cửa sổ tiếp theo sẽ là ngày mai.</span>"
                            )
                        result = False
                    
                    # Apply delay after execution (to prevent crash from rapid calls)
                    try:
                        if not self._apply_action_delay(action):
                            return False
                    except Exception as delay_err:
                        print(f"[EventNotify] ERROR applying delay: {delay_err}")
                        # Continue even if delay fails
                    
                    return result
                except Exception as e6:
                    print(f"[EventNotify] ERROR handling result: {e6}")
                    print(traceback.format_exc())
                    self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi xử lý kết quả: {e6}")
                    return False
                    
            except Exception as e:
                import traceback
                error_msg = str(e)
                error_trace = traceback.format_exc()
                print(f"[EventNotify] FATAL ERROR: {error_msg}")
                print(f"[EventNotify] TRACEBACK:\n{error_trace}")
                self._ui_log(f"<b style='color:red;'>[Event]</b> ❌ Lỗi nghiêm trọng: {error_msg}")
                self._ui_log(f"<pre style='color:red;font-size:10px;'>{self._escape_html(error_trace)}</pre>")
                return False

        elif action.action_type == ActionType.IMAGE_DETECT:
            if bool(getattr(action, "yolo_enabled", False)):
                self._ui_log("<b>[YOLO]</b> Đang nhận diện bằng model ONNX CPU...")
                screenshot = self.capture_window_screenshot()
                if screenshot is None:
                    self._ui_log("<b style='color:red;'>[YOLO]</b> Không thể chụp target window")
                    return False
                try:
                    detector = YoloDetector(
                        model_path=getattr(action, "yolo_model_path", "") or None,
                    )
                    detections = detector.detect(
                        screenshot,
                        confidence=float(getattr(action, "yolo_confidence", 0.25) or 0.25),
                        iou=float(getattr(action, "yolo_iou", 0.45) or 0.45),
                        class_ids=getattr(action, "yolo_class_ids", None),
                    )
                except YoloError as exc:
                    self._ui_log(f"<b style='color:red;'>[YOLO]</b> {self._escape_html(str(exc))}")
                    return False
                except Exception as exc:
                    self._ui_log(f"<b style='color:red;'>[YOLO]</b> Lỗi không xác định: {self._escape_html(str(exc))}")
                    return False

                if not detections:
                    self._ui_log("<b style='color:red;'>[YOLO]</b> Không phát hiện đối tượng phù hợp")
                    return False
                summary = ", ".join(
                    f"{item.class_name or item.class_id}:{item.confidence:.3f}"
                    for item in detections
                )
                self._ui_log(f"<b style='color:green;'>[YOLO]</b> Phát hiện {len(detections)} đối tượng: {summary}")
                return True

            if not action.image_path or not os.path.exists(action.image_path):
                self._ui_log("<b style='color:red;'>[Detect]</b> Thất bại: chưa cấu hình ảnh template")
                return False

            self._ui_log(f"<b>[Detect]</b> Tìm ảnh: {os.path.basename(action.image_path)}")
            threshold = float(getattr(action, "match_threshold", 0.8) or 0.8)
            mask_regions = getattr(action, "mask_regions", None)
            teaching_window_width = getattr(action, "teaching_window_width", None)
            teaching_window_height = getattr(action, "teaching_window_height", None)
            preprocessing_algorithms = getattr(action, "template_matching_algorithms", None)
            
            image_result, score = self.find_image_in_window_with_score(
                action.image_path,
                threshold=threshold,
                multiscale_enabled=bool(getattr(action, "multiscale_enabled", True)),
                mask_regions=mask_regions,
                teaching_window_width=teaching_window_width,
                teaching_window_height=teaching_window_height,
                preprocessing_algorithms=preprocessing_algorithms
            )

            if image_result is None:
                self._ui_log(f"<b style='color:red;'>[Detect]</b> Không tìm thấy ảnh (score: {_format_score(score)} < {threshold})")
                return False

            self._ui_log(f"<b style='color:green;'>[Detect]</b> Tìm thấy ảnh (score: {_format_score(score)})")
            
            if bool(getattr(action, "read_data", False)):
                self._ui_log("<b>[Detect]</b> Đọc dữ liệu từ ảnh...")
                return self.read_data_from_image(image_result, action)
            
            return True

        elif action.action_type == ActionType.DYNAMIC_OCR_CONDITION:
            return self._execute_dynamic_ocr_condition(action)

        elif action.action_type == ActionType.READ_PASSIVE:
            passive_mode = str(getattr(action, "passive_mode", "detect_image") or "detect_image")
            
            if passive_mode == "detect_image":
                # Mode 2: Phát hiện hình ảnh (template matching)
                self._ui_log("<b style='color:blue;'>[Passive]</b> Chế độ: Phát hiện hình ảnh")
                return self._run_passive_detect_image(action)
            else:
                # Mode 1: Đọc dữ liệu (OCR + Gemini + Telegram)
                self._ui_log("<b style='color:blue;'>[Passive]</b> Chế độ: Đọc dữ liệu")
                timeout = float(getattr(action, "timeout", 5.0) or 5.0)
                return self._run_passive_read(action, timeout)

        elif action.action_type == ActionType.WAIT:
            # WAIT action: sleep for specified timeout duration
            wait_time = float(getattr(action, "timeout", 1.0) or 1.0)
            self._ui_log(f"<b style='color:blue;'>[Wait]</b> Chờ {wait_time}s...")
            
            # Use interruptible sleep (check every 100ms for stop signal)
            start_time = time.time()
            while time.time() - start_time < wait_time:
                if self.engine and (not self.engine.is_running or self.engine.should_stop_completely):
                    self._ui_log("<b style='color:orange;'>[Wait]</b> Đã dừng")
                    return False
                remaining = wait_time - (time.time() - start_time)
                time.sleep(min(0.1, remaining))
            
            self._ui_log(f"<b style='color:green;'>[Wait]</b> Hoàn thành chờ {wait_time}s")
            return True

        else:
            self._ui_log(f"<b style='color:red;'>[Execute]</b> Unknown action type: {action.action_type}")
            return False
    
    def execute_with_timeout(self, action: AutoAction, timeout: float = 30.0) -> bool | None:
        """Execute action with timeout for image-based actions.
        
        For MOUSE_CLICK and IMAGE_DETECT actions, repeatedly search for the image
        until found or timeout expires.
        
        For MOUSE_CLICK with coordinate mode, execute immediately without waiting.
        
        Args:
            action: The action to execute
            timeout: Maximum time in seconds to wait for image detection
        
        Returns:
            True: Image found and action executed
            False: Timeout expired without finding image
            None: Cancelled (e.g., settings update)
        """
        # EVENT_NOTIFY should never use execute_with_timeout - it's a one-time check
        if action.action_type == ActionType.EVENT_NOTIFY:
            return self.execute(action)
        
        if action.action_type not in (ActionType.MOUSE_CLICK, ActionType.IMAGE_DETECT, ActionType.DYNAMIC_OCR_CONDITION):
            # For non-image actions, just use regular execute
            return self.execute(action)
        
        # For MOUSE_CLICK with coordinate mode, execute immediately
        if action.action_type == ActionType.MOUSE_CLICK:
            click_by_coordinate = bool(getattr(action, "click_by_coordinate", False))
            if click_by_coordinate:
                return self.execute(action)
        
        # Validate image path
        if action.action_type != ActionType.DYNAMIC_OCR_CONDITION and (not action.image_path or not os.path.exists(action.image_path)):
            self._ui_log("<b style='color:red;'>[Wait]</b> Thất bại: chưa cấu hình ảnh template")
            self._last_wait_diagnostics = {
                "status": "error",
                "reason": "no_image_path",
                "timeout": timeout,
            }
            return False
        
        threshold = float(getattr(action, "match_threshold", 0.8) or 0.8)
        multiscale_enabled = bool(getattr(action, "multiscale_enabled", True))
        
        if action.action_type == ActionType.DYNAMIC_OCR_CONDITION:
            self._ui_log(f"<b>[Wait]</b> Chờ Dynamic OCR Condition trong {timeout}s")
        else:
            self._ui_log(f"<b>[Wait]</b> Tìm ảnh trong {timeout}s: {os.path.basename(action.image_path)}")
        
        start_time = time.time()
        best_score = 0.0
        
        while True:
            # Check for cancellation
            if self.engine and hasattr(self.engine, "stop_requested"):
                if self.engine.stop_requested:
                    self._ui_log("<b style='color:orange;'>[Wait]</b> Đã hủy")
                    self._last_wait_diagnostics = {
                        "status": "cancelled",
                        "timeout": timeout,
                        "best_score": best_score,
                        "threshold": threshold,
                    }
                    return None
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                self._ui_log(f"<b style='color:red;'>[Wait]</b> Hết thời gian ({elapsed:.1f}s > {timeout}s, score: {best_score:.3f} < {threshold})")
                self._last_wait_diagnostics = {
                    "status": "timeout",
                    "elapsed": elapsed,
                    "timeout": timeout,
                    "best_score": best_score,
                    "threshold": threshold,
                }
                return False
            
            # Try to find image
            mask_regions = getattr(action, "mask_regions", None)
            teaching_window_width = getattr(action, "teaching_window_width", None)
            teaching_window_height = getattr(action, "teaching_window_height", None)
            preprocessing_algorithms = getattr(action, "template_matching_algorithms", None)
            
            image_result, score = self.find_image_in_window_with_score(
                action.image_path,
                threshold=threshold,
                multiscale_enabled=multiscale_enabled,
                mask_regions=mask_regions,
                teaching_window_width=teaching_window_width,
                teaching_window_height=teaching_window_height,
                preprocessing_algorithms=preprocessing_algorithms
            )
            
            best_score = max(best_score, score)
            
            if image_result is not None:
                # Image found!
                self._ui_log(f"<b style='color:green;'>[Wait]</b> Tìm thấy ảnh (score: {_format_score(score)}, elapsed: {elapsed:.1f}s)")
                self._last_wait_diagnostics = {
                    "status": "found",
                    "score": score,
                    "threshold": threshold,
                    "elapsed": elapsed,
                    "timeout": timeout,
                }
                
                # Execute the action
                if action.action_type == ActionType.MOUSE_CLICK:
                    click_x = int(getattr(action, "click_x", 0) or 0)
                    click_y = int(getattr(action, "click_y", 0) or 0)
                    screen_x, screen_y, client_x, client_y = self.calculate_click_position(image_result, click_x, click_y)
                    
                    self._ui_log(f"<b>[Wait]</b> Click tại ({screen_x}, {screen_y})")
                    use_alt = bool(getattr(action, "alt_click", False))
                    self.mouse_controller.click_with_optional_alt(screen_x, screen_y, client_x, client_y, use_alt)
                
                return True
            
            # Wait a bit before retrying
            time.sleep(0.1)
    
    def calculate_click_position(self, image_result: tuple, click_x: int = None, click_y: int = None) -> tuple:
        """Calculate screen click position from image detection result.
        
        Args:
            image_result: (top_left_x, top_left_y, img_w, img_h [, scale]) - vị trí template trong client area
            click_x, click_y: Tọa độ click trong ảnh template (relative to top-left của template)
        
        Returns: (screen_x, screen_y, client_x, client_y) hoặc None
        """
        if not image_result or len(image_result) < 4:
            return None

        # Unpack image result
        if len(image_result) >= 5:
            top_left_x, top_left_y, img_w, img_h, scale = image_result[:5]
        else:
            top_left_x, top_left_y, img_w, img_h = image_result[:4]
            scale = 1.0
        
        # Nếu không có click point, click vào center của template
        if click_x is None:
            click_x = img_w // 2
        if click_y is None:
            click_y = img_h // 2
        
        # Scale click offset nếu template được scale
        scaled_click_x = int(round(click_x * float(scale)))
        scaled_click_y = int(round(click_y * float(scale)))
        
        # Tính vị trí click trong client coordinates
        # client_x, client_y = vị trí top-left của template + offset trong template
        client_x = top_left_x + scaled_click_x
        client_y = top_left_y + scaled_click_y
        
        # Debug log
        self._ui_log(f"<span style='color:gray;'>[Debug] Template at ({top_left_x},{top_left_y}), size {img_w}x{img_h}, scale={scale:.2f}</span>")
        self._ui_log(f"<span style='color:gray;'>[Debug] Click offset: ({click_x},{click_y}) -> scaled: ({scaled_click_x},{scaled_click_y})</span>")
        self._ui_log(f"<span style='color:gray;'>[Debug] Client click pos: ({client_x},{client_y})</span>")
        
        if not self.target_window_hwnd:
            return client_x, client_y, client_x, client_y
        
        try:
            import win32gui
            
            # Kiểm tra click có nằm trong client area không
            client_rect = win32gui.GetClientRect(self.target_window_hwnd)
            client_w = client_rect[2] - client_rect[0]
            client_h = client_rect[3] - client_rect[1]
            
            if client_x < 0 or client_y < 0 or client_x >= client_w or client_y >= client_h:
                self._ui_log(f"<b style='color:red;'>[Click]</b> Bỏ qua: tọa độ ({client_x},{client_y}) nằm ngoài client area ({client_w}x{client_h})")
                return None
            
            # Convert từ client coordinates sang screen coordinates
            # ClientToScreen chuyển (0,0) của client area sang screen coordinates
            client_origin = win32gui.ClientToScreen(self.target_window_hwnd, (0, 0))
            screen_x = client_origin[0] + client_x
            screen_y = client_origin[1] + client_y
            
            self._ui_log(f"<span style='color:gray;'>[Debug] Screen click pos: ({screen_x},{screen_y})</span>")
            
            return screen_x, screen_y, client_x, client_y
        except Exception as e:
            self._ui_log(f"<b style='color:red;'>[Click]</b> Lỗi tính tọa độ: {e}")
            return client_x, client_y, client_x, client_y

    # ============ Special Event Tracking ============

    def _setup_special_event_subscriptions(self, action: AutoAction, hwnd: int) -> bool:
        """Subscribe enabled special events to ScreenScanService."""
        from .imperial_guardian_handler import ImperialGuardianHandler
        from .golden_invasion_handler import GoldenInvasionHandler
        from .golden_invasion_sub_handler import GoldenInvasionSubHandler
        from .monster_invasion_handler import MonsterInvasionHandler
        from .screen_scan_service import ScreenScanService, OCRSubscription
        from .white_wizard_red_dragon_handler import WhiteWizardRedDragonHandler

        service = ScreenScanService.get_instance()
        handler_key = f"{id(action)}_{getattr(action, 'name', 'unknown')}"
        if not hasattr(self, '_special_event_handlers'):
            self._special_event_handlers = {}

        subscribed_any = False

        # Imperial Guardian
        if getattr(action, "imperial_guardian_enabled", False):
            x1 = getattr(action, "imperial_guardian_teaching_corner_x1", 0)
            y1 = getattr(action, "imperial_guardian_teaching_corner_y1", 0)
            x2 = getattr(action, "imperial_guardian_teaching_corner_x2", 0)
            y2 = getattr(action, "imperial_guardian_teaching_corner_y2", 0)

            if x2 <= x1 or y2 <= y1 or x1 < 0 or y1 < 0:
                self._ui_log("<b style='color:orange;'>[Special Event]</b> ROI not configured, skipping Imperial Guardian")
            else:
                roi = (x1, y1, x2 - x1, y2 - y1)
                delay_minutes = getattr(action, "imperial_guardian_no_player_alert_delay", 10)

                handler = ImperialGuardianHandler(
                    telegram_notifier=getattr(self, 'telegram_notifier', None),
                    ui_log=self._ui_log,
                    delay_minutes=delay_minutes,
                    match_threshold=getattr(action, "imperial_guardian_match_threshold", 70.0),
                )
                self._special_event_handlers[handler_key] = handler

                action_id = f"special_event:{handler_key}:imperial_guardian"
                ocr_engine = getattr(action, "imperial_guardian_ocr_engine", "auto")

                self._ui_log(f"<b style='color:cyan;'>[Special Event]</b> Imperial Guardian setup: engine={ocr_engine}, roi={roi}, delay={delay_minutes}min")

                def on_ocr_result(text: str):
                    handler.on_ocr_text(text)

                sub = OCRSubscription(
                    action_id=action_id,
                    hwnd=hwnd,
                    roi=roi,
                    ocr_engine=ocr_engine,
                    ocr_algorithms=getattr(action, "imperial_guardian_ocr_algorithms", []) or [],
                    callback=on_ocr_result,
                )
                service.subscribe(sub)
                self._ui_log(f"<b style='color:green;'>[Special Event]</b> Imperial Guardian: subscribed (delay={delay_minutes}min)")
                subscribed_any = True
        else:
            self._ui_log("<b style='color:orange;'>[Special Event]</b> Imperial Guardian disabled")

        # Golden Invasion
        if getattr(action, "golden_invasion_enabled", False):
            x1 = getattr(action, "golden_invasion_channel_roi_x1", 0)
            y1 = getattr(action, "golden_invasion_channel_roi_y1", 0)
            x2 = getattr(action, "golden_invasion_channel_roi_x2", 0)
            y2 = getattr(action, "golden_invasion_channel_roi_y2", 0)
            if x2 <= x1 or y2 <= y1:
                self._ui_log("<b style='color:orange;'>[Special Event]</b> Golden Invasion: Channel ROI chưa cấu hình, bỏ qua")
            else:
                nx1 = getattr(action, "golden_invasion_notify_roi_x1", 0)
                ny1 = getattr(action, "golden_invasion_notify_roi_y1", 0)
                nx2 = getattr(action, "golden_invasion_notify_roi_x2", 0)
                ny2 = getattr(action, "golden_invasion_notify_roi_y2", 0)
                if nx2 <= nx1 or ny2 <= ny1:
                    self._ui_log("<b style='color:orange;'>[Special Event]</b> Golden Invasion: Notify ROI chưa cấu hình, bỏ qua")
                else:
                    channel_roi = (x1, y1, x2 - x1, y2 - y1)
                    notify_roi = (nx1, ny1, nx2 - nx1, ny2 - ny1)

                    gi_handler = GoldenInvasionHandler(
                        server_time=getattr(action, "golden_invasion_server_time", "01:30"),
                        match_threshold=getattr(action, "golden_invasion_match_threshold", 70.0),
                        telegram_notifier=getattr(self, 'telegram_notifier', None),
                        log_signal_emit=self._ui_log,
                    )
                    self._special_event_handlers[f"{handler_key}_gi"] = gi_handler
                    pair_group_id = f"golden_invasion:{handler_key}"

                    sub_channel = OCRSubscription(
                        action_id=f"special_event:{handler_key}:golden_invasion:channel",
                        hwnd=hwnd,
                        roi=channel_roi,
                        ocr_engine=getattr(action, "golden_invasion_channel_ocr_engine", "auto"),
                        ocr_algorithms=getattr(action, "golden_invasion_channel_ocr_algorithms", []) or [],
                        callback=gi_handler.on_channel_text,
                        pair_group_id=pair_group_id,
                        pair_role="channel",
                        pair_log_callback=self._log_golden_invasion_ocr_pair,
                    )
                    service.subscribe(sub_channel)

                    sub_notify = OCRSubscription(
                        action_id=f"special_event:{handler_key}:golden_invasion:notify",
                        hwnd=hwnd,
                        roi=notify_roi,
                        ocr_engine=getattr(action, "golden_invasion_notify_ocr_engine", "auto"),
                        ocr_algorithms=getattr(action, "golden_invasion_notify_ocr_algorithms", []) or [],
                        callback=gi_handler.on_notify_text,
                        pair_group_id=pair_group_id,
                        pair_role="notify",
                        pair_log_callback=self._log_golden_invasion_ocr_pair,
                    )
                    service.subscribe(sub_notify)

                    server_time = getattr(action, "golden_invasion_server_time", "01:30")
                    self._ui_log(f"<b style='color:green;'>[Special Event]</b> Golden Invasion: subscribed (server_time={server_time})")
                    subscribed_any = True

        # Monster Invasion
        if getattr(action, "monster_invasion_enabled", False):
            sub_handlers = []
            if getattr(action, "monster_invasion_golden_invasion_enabled", False):
                sub_handlers.append(GoldenInvasionSubHandler(
                    server_time=getattr(action, "monster_invasion_golden_invasion_server_time", "01:30"),
                    match_threshold=getattr(action, "monster_invasion_match_threshold", 70.0),
                    telegram_notifier=getattr(self, 'telegram_notifier', None),
                    log_signal_emit=self._ui_log,
                ))
            if getattr(action, "monster_invasion_white_wizard_red_dragon_enabled", False):
                sub_handlers.append(WhiteWizardRedDragonHandler(
                    match_threshold=getattr(action, "monster_invasion_match_threshold", 70.0),
                    telegram_notifier=getattr(self, 'telegram_notifier', None),
                    log_signal_emit=self._ui_log,
                ))

            if not sub_handlers:
                self._ui_log("<b style='color:orange;'>[Special Event]</b> Monster Invasion: no sub-event enabled, skipping")
            else:
                cx1 = getattr(action, "monster_invasion_channel_roi_x1", 0)
                cy1 = getattr(action, "monster_invasion_channel_roi_y1", 0)
                cx2 = getattr(action, "monster_invasion_channel_roi_x2", 0)
                cy2 = getattr(action, "monster_invasion_channel_roi_y2", 0)
                nx1 = getattr(action, "monster_invasion_notify_roi_x1", 0)
                ny1 = getattr(action, "monster_invasion_notify_roi_y1", 0)
                nx2 = getattr(action, "monster_invasion_notify_roi_x2", 0)
                ny2 = getattr(action, "monster_invasion_notify_roi_y2", 0)
                if cx2 <= cx1 or cy2 <= cy1:
                    self._ui_log("<b style='color:orange;'>[Special Event]</b> Monster Invasion: Channel ROI chưa cấu hình, bỏ qua")
                elif nx2 <= nx1 or ny2 <= ny1:
                    self._ui_log("<b style='color:orange;'>[Special Event]</b> Monster Invasion: Notify ROI chưa cấu hình, bỏ qua")
                else:
                    mi_handler = MonsterInvasionHandler(sub_handlers=sub_handlers, log_signal_emit=self._ui_log)
                    self._special_event_handlers[f"{handler_key}_mi"] = mi_handler
                    pair_group_id = f"monster_invasion:{handler_key}"
                    channel_roi = (cx1, cy1, cx2 - cx1, cy2 - cy1)
                    notify_roi = (nx1, ny1, nx2 - nx1, ny2 - ny1)

                    service.subscribe(OCRSubscription(
                        action_id=f"special_event:{handler_key}:monster_invasion:channel",
                        hwnd=hwnd,
                        roi=channel_roi,
                        ocr_engine=getattr(action, "monster_invasion_channel_ocr_engine", "auto"),
                        ocr_algorithms=getattr(action, "monster_invasion_channel_ocr_algorithms", []) or [],
                        callback=mi_handler.on_channel_text,
                        pair_group_id=pair_group_id,
                        pair_role="channel",
                    ))
                    service.subscribe(OCRSubscription(
                        action_id=f"special_event:{handler_key}:monster_invasion:notify",
                        hwnd=hwnd,
                        roi=notify_roi,
                        ocr_engine=getattr(action, "monster_invasion_notify_ocr_engine", "auto"),
                        ocr_algorithms=getattr(action, "monster_invasion_notify_ocr_algorithms", []) or [],
                        callback=mi_handler.on_notify_text,
                        pair_group_id=pair_group_id,
                        pair_role="notify",
                    ))
                    self._ui_log(f"<b style='color:green;'>[Special Event]</b> Monster Invasion: subscribed ({len(sub_handlers)} sub-event(s))")
                    subscribed_any = True

        return subscribed_any

    def _log_golden_invasion_ocr_pair(self, group_id: str, texts: dict) -> None:
        """Log Golden Invasion channel/notify OCR pair from one screenshot."""
        import re
        from .event_tracking_helper import normalize_ocr_text
        from .golden_invasion_handler import PATTERNS_KILL

        def _short(value: str, limit: int = 120) -> str:
            value = " ".join(str(value or "").split())
            if len(value) <= limit:
                return value
            return value[:limit - 3] + "..."

        channel_text = str(texts.get("channel", "") or "")
        notify_text = str(texts.get("notify", "") or "")
        normalized_notify = normalize_ocr_text(notify_text)

        matched_patterns = []
        for idx, pattern in enumerate(PATTERNS_KILL, 1):
            if re.search(pattern, normalized_notify):
                matched_patterns.append(f"P{idx}")

        matched = bool(matched_patterns)
        match_label = ",".join(matched_patterns) if matched_patterns else "none"
        plain = (
            f"[Golden Invasion OCR Pair] group={group_id} "
            f"matched={matched} patterns={match_label} | "
            f"channel=\"{_short(channel_text)}\" | notify=\"{_short(notify_text)}\""
        )
        print(plain)
        self._ui_log(
            "<b>[Golden Invasion OCR Pair]</b> "
            f"matched=<b>{matched}</b> patterns=<code>{match_label}</code> | "
            f"channel=<code>{self._escape_html(_short(channel_text))}</code> | "
            f"notify=<code>{self._escape_html(_short(notify_text))}</code>"
        )
    
    def _teardown_special_event_subscriptions(self, action: AutoAction) -> None:
        """Unsubscribe special events from ScreenScanService."""
        from .screen_scan_service import ScreenScanService

        handler_key = f"{id(action)}_{getattr(action, 'name', 'unknown')}"
        service = ScreenScanService.get_instance()

        # Imperial Guardian
        if hasattr(self, '_special_event_handlers') and handler_key in self._special_event_handlers:
            handler = self._special_event_handlers[handler_key]
            handler.reset()
            del self._special_event_handlers[handler_key]

        try:
            service.unsubscribe(f"special_event:{handler_key}:imperial_guardian")
            self._ui_log(f"<b style='color:green;'>[Special Event]</b> Imperial Guardian: unsubscribed")
        except Exception as e:
            self._ui_log(f"<b style='color:orange;'>[Special Event]</b> Failed to unsubscribe Imperial Guardian: {e}")

        # Golden Invasion
        if hasattr(self, '_special_event_handlers') and f"{handler_key}_gi" in self._special_event_handlers:
            gi_handler = self._special_event_handlers[f"{handler_key}_gi"]
            gi_handler.reset()
            del self._special_event_handlers[f"{handler_key}_gi"]

        try:
            service.unsubscribe(f"special_event:{handler_key}:golden_invasion:channel")
        except Exception:
            pass
        try:
            service.unsubscribe(f"special_event:{handler_key}:golden_invasion:notify")
            self._ui_log("<b style='color:green;'>[Special Event]</b> Golden Invasion: unsubscribed")
        except Exception as e:
            self._ui_log(f"<b style='color:orange;'>[Special Event]</b> Failed to unsubscribe Golden Invasion: {e}")

        # Monster Invasion
        if hasattr(self, '_special_event_handlers') and f"{handler_key}_mi" in self._special_event_handlers:
            mi_handler = self._special_event_handlers[f"{handler_key}_mi"]
            mi_handler.reset()
            del self._special_event_handlers[f"{handler_key}_mi"]

        try:
            service.unsubscribe(f"special_event:{handler_key}:monster_invasion:channel")
        except Exception:
            pass
        try:
            service.unsubscribe(f"special_event:{handler_key}:monster_invasion:notify")
            self._ui_log("<b style='color:green;'>[Special Event]</b> Monster Invasion: unsubscribed")
        except Exception as e:
            self._ui_log(f"<b style='color:orange;'>[Special Event]</b> Failed to unsubscribe Monster Invasion: {e}")
