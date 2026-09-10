"""Window Capture - Screenshot capture from target window."""

import ctypes
import os
import time
from ctypes import wintypes

import numpy as np
import win32con
import win32gui
import win32ui

# Windows API constants for PrintWindow
PW_CLIENTONLY = 0x00000001  # Client area only
PW_RENDERFULLCONTENT = 0x00000002  # Full content for some DirectX/OpenGL windows

# Load PrintWindow function from user32.dll
user32 = ctypes.windll.user32
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, ctypes.c_uint]
user32.PrintWindow.restype = wintypes.BOOL

# DPI Awareness constants
PROCESS_PER_MONITOR_DPI_AWARE = 2

# DPI Awareness Context (Windows 10 1607+)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4


def _set_dpi_awareness():
    """Set DPI awareness to get high-quality screenshots."""
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        return True
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
        return True
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return True
    except Exception:
        pass

    return False


class WindowCapture:
    """Handle window screenshot capture."""

    _dpi_aware_set = False

    def __init__(self, target_window_hwnd=None, ui_log_func=None, debug_output: bool = True):
        self.target_window_hwnd = target_window_hwnd
        self.ui_log = ui_log_func or (lambda x: None)
        self.debug_output = bool(debug_output)

        if not WindowCapture._dpi_aware_set:
            _set_dpi_awareness()
            WindowCapture._dpi_aware_set = True

    def set_target_window(self, hwnd):
        """Set target window handle."""
        self.target_window_hwnd = hwnd

    def _log_debug(self, message: str) -> None:
        """Emit lightweight capture diagnostics."""
        if self.debug_output:
            try:
                print(f"[WindowCapture] {message}")
            except Exception:
                pass
        try:
            self.ui_log(f"<span style='color:gray;'>[WindowCapture]</span> {message}")
        except Exception:
            pass

    def capture(self) -> np.ndarray | None:
        """Capture a screenshot of the target window."""
        if not self.target_window_hwnd:
            return None

        hwndDC = None
        mfcDC = None
        saveDC = None
        bitmap = None
        screen_dc = None
        screen_mfc = None
        capture_mode = str(os.environ.get("AUTOAPP_CAPTURE_MODE", "auto") or "auto").strip().lower()
        capture_started = time.perf_counter()

        try:
            rect = win32gui.GetClientRect(self.target_window_hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            if width <= 0 or height <= 0:
                self._log_debug(f"Skip capture hwnd={self.target_window_hwnd} invalid_size={width}x{height}")
                return None

            hwndDC = win32gui.GetWindowDC(self.target_window_hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(bitmap)

            result = False
            method_used = "none"

            if capture_mode not in {"bitblt", "screen"}:
                self._log_debug(
                    f"Capture start hwnd={self.target_window_hwnd} size={width}x{height} mode={capture_mode}"
                )
                pw_started = time.perf_counter()
                result = user32.PrintWindow(self.target_window_hwnd, saveDC.GetSafeHdc(), PW_CLIENTONLY)
                self._log_debug(
                    f"PrintWindow(PW_CLIENTONLY) result={bool(result)} elapsed_ms={(time.perf_counter() - pw_started) * 1000:.2f}"
                )
                if result:
                    method_used = "printwindow_client"

            if not result and capture_mode in {"auto", "printwindow", "renderfullcontent"}:
                pw_full_started = time.perf_counter()
                result = user32.PrintWindow(self.target_window_hwnd, saveDC.GetSafeHdc(), PW_RENDERFULLCONTENT)
                self._log_debug(
                    f"PrintWindow(PW_RENDERFULLCONTENT) result={bool(result)} elapsed_ms={(time.perf_counter() - pw_full_started) * 1000:.2f}"
                )
                if result:
                    method_used = "printwindow_fullcontent"

            if not result:
                client_rect = win32gui.GetClientRect(self.target_window_hwnd)
                client_x, client_y, _, _ = client_rect
                client_pos = win32gui.ClientToScreen(self.target_window_hwnd, (client_x, client_y))

                screen_dc = win32gui.GetWindowDC(0)
                screen_mfc = win32ui.CreateDCFromHandle(screen_dc)
                bitblt_started = time.perf_counter()
                result = saveDC.BitBlt((0, 0), (width, height), screen_mfc, client_pos, win32con.SRCCOPY)
                self._log_debug(
                    f"BitBlt result={bool(result)} elapsed_ms={(time.perf_counter() - bitblt_started) * 1000:.2f}"
                )
                if result:
                    method_used = "bitblt"

            if not result:
                self._log_debug(
                    f"Capture failed hwnd={self.target_window_hwnd} total_elapsed_ms={(time.perf_counter() - capture_started) * 1000:.2f}"
                )
                return None

            bmpstr = bitmap.GetBitmapBits(True)
            arr = np.frombuffer(bmpstr, dtype=np.uint8).reshape((height, width, 4))
            img_bgr = arr[:, :, :3].copy()
            self._log_debug(
                f"Capture success hwnd={self.target_window_hwnd} method={method_used} total_elapsed_ms={(time.perf_counter() - capture_started) * 1000:.2f}"
            )
            return img_bgr

        except Exception as e:
            self._log_debug(f"Capture exception hwnd={self.target_window_hwnd}: {e}")
            self.ui_log(f"<b style='color:red;'>[Capture]</b> Lỗi: {e}")
            return None
        finally:
            try:
                if bitmap:
                    win32gui.DeleteObject(bitmap.GetHandle())
            except Exception:
                pass
            try:
                if saveDC:
                    saveDC.DeleteDC()
            except Exception:
                pass
            try:
                if mfcDC:
                    mfcDC.DeleteDC()
            except Exception:
                pass
            try:
                if hwndDC:
                    win32gui.ReleaseDC(self.target_window_hwnd, hwndDC)
            except Exception:
                pass
            try:
                if screen_mfc:
                    screen_mfc.DeleteDC()
            except Exception:
                pass
            try:
                if screen_dc:
                    win32gui.ReleaseDC(0, screen_dc)
            except Exception:
                pass
