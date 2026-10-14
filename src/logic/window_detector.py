import win32gui
import win32con
import win32process
import win32api
from typing import List, Optional, Tuple

class WindowDetector:
    """Detect top-level MU game windows without including helper UI windows."""

    GAME_TITLE_PREFIXES = (
        "mu gamethuvn - season 21",
        "mu online - gamethuvn.com",
    )

    @staticmethod
    def is_game_window_title(title: str) -> bool:
        """Return True only for known MU game title formats."""
        normalized = " ".join(str(title or "").split()).casefold()
        if not normalized:
            return False

        for prefix in WindowDetector.GAME_TITLE_PREFIXES:
            if normalized == prefix or normalized.startswith(f"{prefix} ("):
                return True
        return False

    @staticmethod
    def find_game_windows(include_invisible: bool = False) -> List[Tuple[int, str]]:
        """Find visible MU game windows with stricter title filtering."""
        windows = []

        def enum_windows_callback(hwnd, windows_list):
            if include_invisible or win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd) or ""
                if WindowDetector.is_game_window_title(title):
                    windows_list.append((hwnd, title))
            return True

        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows

    @staticmethod
    def _get_process_exe_name(hwnd: int) -> str:
        """Return process exe name (basename) for a window handle, or empty string."""
        try:
            _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            if not pid:
                return ""
            # Query full image name
            h_process = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                False,
                pid,
            )
            try:
                exe_path = win32process.GetModuleFileNameEx(h_process, 0)
            finally:
                win32api.CloseHandle(h_process)
            if not exe_path:
                return ""
            return exe_path.split("\\")[-1]
        except Exception:
            return ""

    @staticmethod
    def find_windows_by_title(partial_title: str, include_invisible: bool = False) -> List[Tuple[int, str]]:
        """Tìm tất cả windows có title chứa partial_title"""
        windows = []
        
        def enum_windows_callback(hwnd, windows_list):
            if include_invisible or win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd) or ""
                if partial_title.lower() in window_title.lower():
                    windows_list.append((hwnd, window_title))
            return True
        
        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows

    @staticmethod
    def find_windows_by_process_name(partial_exe_name: str, include_invisible: bool = False) -> List[Tuple[int, str]]:
        """Tìm tất cả windows theo tên process (exe) chứa partial_exe_name.
        Trả về list (hwnd, window_title)."""
        windows = []

        def enum_windows_callback(hwnd, windows_list):
            if not (include_invisible or win32gui.IsWindowVisible(hwnd)):
                return True
            title = win32gui.GetWindowText(hwnd) or ""
            exe_name = WindowDetector._get_process_exe_name(hwnd)
            if exe_name and partial_exe_name.lower() in exe_name.lower():
                windows_list.append((hwnd, title))
            return True

        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows
    
    @staticmethod
    def list_all_windows() -> List[Tuple[int, str, str]]:
        """Liệt kê tất cả windows (để debug)"""
        windows = []
        
        def enum_windows_callback(hwnd, windows_list):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                windows_list.append((hwnd, window_title, class_name))
            return True
        
        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows
    
    @staticmethod
    def get_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
        """Lấy rectangle của window (left, top, right, bottom)"""
        return win32gui.GetWindowRect(hwnd)
    
    @staticmethod
    def set_foreground_window(hwnd: int):
        """Đưa window lên foreground"""
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
