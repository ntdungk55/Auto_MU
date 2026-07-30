"""Mouse Controller - Handle mouse input operations."""

import ctypes
import time
import win32gui
import win32con

try:
    import keyboard
except Exception:
    keyboard = None


# SendInput structures for dwExtraInfo support
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("_input", _INPUT_UNION),
    ]


class MouseController:
    """Handle mouse input operations."""
    
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_ABSOLUTE = 0x8000
    MOUSEEVENTF_MOVE = 0x0001
    
    INPUT_MOUSE = 0
    
    # Magic marker to identify tool-generated events
    TOOL_MARKER = 0xAB10

    @staticmethod
    def release_modifier_keys():
        """Best-effort release for common modifier keys to avoid stuck input state."""
        try:
            if keyboard:
                for key_name in ("alt", "ctrl", "shift", "left windows", "right windows"):
                    try:
                        keyboard.release(key_name)
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            user32 = ctypes.windll.user32
            key_up = 0x0002
            for vk_code in (0x12, 0x11, 0x10, 0x5B, 0x5C):
                try:
                    user32.keybd_event(vk_code, 0, key_up, 0)
                except Exception:
                    pass
        except Exception:
            pass
    
    def __init__(self, target_window_hwnd=None, ui_log_func=None):
        """Initialize mouse controller.
        
        Args:
            target_window_hwnd: Target window handle
            ui_log_func: Optional logging function
        """
        self.target_window_hwnd = target_window_hwnd
        self.ui_log = ui_log_func or (lambda x: None)
        # Pointer for dwExtraInfo
        self._extra_info = ctypes.c_ulong(self.TOOL_MARKER)
    
    def set_target_window(self, hwnd):
        """Set target window handle."""
        self.target_window_hwnd = hwnd
    
    def _send_mouse_input(self, flags: int, x: int = 0, y: int = 0):
        """Send mouse input using SendInput API with dwExtraInfo marker.
        
        Args:
            flags: Mouse event flags
            x: Absolute X coordinate (0-65535 normalized)
            y: Absolute Y coordinate (0-65535 normalized)
        """
        inp = INPUT()
        inp.type = self.INPUT_MOUSE
        inp.mi.dx = x
        inp.mi.dy = y
        inp.mi.mouseData = 0
        inp.mi.dwFlags = flags
        inp.mi.time = 0
        inp.mi.dwExtraInfo = ctypes.pointer(self._extra_info)
        
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    
    def _screen_to_absolute(self, screen_x: int, screen_y: int) -> tuple[int, int]:
        """Convert screen coordinates to absolute coordinates (0-65535).
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            
        Returns:
            Tuple of (abs_x, abs_y) in 0-65535 range
        """
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)
        abs_x = int(screen_x * 65535 / screen_width)
        abs_y = int(screen_y * 65535 / screen_height)
        return abs_x, abs_y
    
    @staticmethod
    def click_at(x: int, y: int, delay_before_click: float = 0.05):
        """Click tại tọa độ x, y (legacy method without marker)
        
        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
            delay_before_click: Delay after moving cursor before clicking (seconds)
        """
        # Di chuyển chuột đến vị trí
        ctypes.windll.user32.SetCursorPos(x, y)
        # Đợi một chút để chuột di chuyển đến đúng vị trí
        time.sleep(delay_before_click)
        # Click
        ctypes.windll.user32.mouse_event(MouseController.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        # Giảm thời gian giữ chuột (tránh bị hiểu nhầm click đúp)
        time.sleep(0.005)
        ctypes.windll.user32.mouse_event(MouseController.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    
    def click_at_with_marker(self, x: int, y: int, delay_before_click: float = 0.05):
        """Click tại tọa độ x, y với dwExtraInfo marker.
        
        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
            delay_before_click: Delay after moving cursor before clicking (seconds)
        """
        # Move cursor first
        ctypes.windll.user32.SetCursorPos(x, y)
        time.sleep(delay_before_click)
        
        # Send click with marker
        self._send_mouse_input(self.MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.005)
        self._send_mouse_input(self.MOUSEEVENTF_LEFTUP)
    
    def click_at_client(self, client_x: int, client_y: int):
        """Gửi click trực tiếp vào window bằng PostMessage với tọa độ client.
        Một số game ignore SetCursorPos/mouse_event (raw input), nên PostMessage có thể giúp.
        
        Args:
            client_x: Client area X coordinate
            client_y: Client area Y coordinate
        """
        if not self.target_window_hwnd:
            return
        try:
            # lParam: low word = x, high word = y
            lparam = (int(client_y) << 16) | (int(client_x) & 0xFFFF)
            win32gui.PostMessage(self.target_window_hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
            win32gui.PostMessage(self.target_window_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
            win32gui.PostMessage(self.target_window_hwnd, win32con.WM_LBUTTONUP, 0, lparam)
        except Exception as e:
            self.ui_log(f"<b style='color:red;'>[Click]</b> PostMessage click lỗi: {e}")
    
    def click_with_optional_alt(self, screen_x: int, screen_y: int, client_x: int, client_y: int, use_alt: bool = False):
        """Click once, optionally holding ALT during the click (ALT+LMB).
        Uses SendInput with dwExtraInfo marker to identify tool-generated events.
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            client_x: Client area X coordinate
            client_y: Client area Y coordinate
            use_alt: Whether to hold ALT during click
        """
        if use_alt and keyboard:
            try:
                keyboard.press("alt")
                time.sleep(0.01)
            except Exception:
                pass
        try:
            # Use click_at_with_marker to include dwExtraInfo
            self.click_at_with_marker(screen_x, screen_y, delay_before_click=0.075)
            # Fallback to PostMessage if environment variable set
            import os
            if os.environ.get("CLICK_FALLBACK_POSTMESSAGE") == "1":
                self.click_at_client(client_x, client_y)
        finally:
            if use_alt and keyboard:
                try:
                    keyboard.release("alt")
                except Exception:
                    pass
            if use_alt:
                self.release_modifier_keys()
    
    def move_mouse_away(self):
        """Move mouse cursor outside of the game window to avoid hover/tooltip affecting template matching."""
        if not self.target_window_hwnd:
            return
        try:
            l, t, r, b = win32gui.GetWindowRect(self.target_window_hwnd)
            # Prefer moving to bottom-right outside the window
            tx = int(r + 20)
            ty = int(b + 20)

            # Clamp to virtual screen to avoid moving outside any monitor
            try:
                SM_XVIRTUALSCREEN = 76
                SM_YVIRTUALSCREEN = 77
                SM_CXVIRTUALSCREEN = 78
                SM_CYVIRTUALSCREEN = 79
                vx = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
                vy = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
                vw = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
                vh = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
                tx = max(vx, min(tx, vx + vw - 1))
                ty = max(vy, min(ty, vy + vh - 1))
            except Exception:
                pass

            ctypes.windll.user32.SetCursorPos(tx, ty)
        except Exception:
            return
    
    def block_input(self, block: bool) -> bool:
        """Block or unblock user input using Windows BlockInput API.
        
        Args:
            block: True to block input, False to unblock
            
        Returns:
            True if successful, False if failed
            
        Note:
            Requires admin rights to work properly.
            If fails, tool continues running normally.
        """
        try:
            result = ctypes.windll.user32.BlockInput(1 if block else 0)
            return bool(result)
        except Exception as e:
            if self.ui_log:
                self.ui_log(f"<b style='color:orange;'>[BlockInput]</b> Lỗi: {e}")
            return False
