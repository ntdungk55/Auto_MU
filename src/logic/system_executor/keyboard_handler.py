"""Keyboard Handler - SendInput keyboard logic extracted from SystemExecutor."""

import ctypes
from ctypes import wintypes
from typing import Callable


class KeyboardHandler:
    """Keyboard input via Windows SendInput API (bypasses BlockInput)."""

    def __init__(self, ui_log_func: Callable[[str], None]):
        """Initialize KeyboardHandler.

        Args:
            ui_log_func: Function to log UI messages
        """
        self._ui_log = ui_log_func

    def send_key(self, key_str: str) -> bool:
        """Send keyboard input using SendInput API.

        Args:
            key_str: Key string (e.g., 'a', 'ctrl+c', 'f1')

        Returns:
            True if successful, False otherwise
        """
        try:
            # Complex hotkeys still use keyboard library; single special keys use SendInput below.
            if '+' in key_str:
                import keyboard
                keyboard.press_and_release(key_str)
                return True

            # Build SendInput structures
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                ULONG_PTR = ctypes.c_ulonglong
            else:
                ULONG_PTR = ctypes.c_ulong

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR),
                ]

            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR),
                ]

            class HARDWAREINPUT(ctypes.Structure):
                _fields_ = [
                    ("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD),
                ]

            class INPUT(ctypes.Structure):
                class _INPUT_UNION(ctypes.Union):
                    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]
                _anonymous_ = ("_input",)
                _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT_UNION)]

            INPUT_KEYBOARD = 1
            KEYEVENTF_KEYUP = 0x0002
            KEYEVENTF_SCANCODE = 0x0008
            KEYEVENTF_UNICODE = 0x0004
            KEYEVENTF_EXTENDEDKEY = 0x0001
            VK_SHIFT = 0x10
            VK_CONTROL = 0x11
            VK_MENU = 0x12
            TOOL_MARKER = 0xAB10

            SendInput = ctypes.windll.user32.SendInput
            MapVirtualKeyW = ctypes.windll.user32.MapVirtualKeyW
            MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
            MapVirtualKeyW.restype = wintypes.UINT

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
                    shift_state = (vk >> 8) & 0xFF

            def _mk_key_input(vk_c: int, is_up: bool) -> INPUT:
                sc = int(MapVirtualKeyW(vk_c, 0)) & 0xFF
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki.wVk = 0
                inp.ki.wScan = sc
                flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if is_up else 0)
                if vk_c in extended_vk_codes:
                    flags |= KEYEVENTF_EXTENDEDKEY
                inp.ki.dwFlags = flags
                inp.ki.time = 0
                inp.ki.dwExtraInfo = TOOL_MARKER
                return inp

            def _mk_unicode_input(ch: str, is_up: bool) -> INPUT:
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki.wVk = 0
                inp.ki.wScan = ord(ch)
                inp.ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if is_up else 0)
                inp.ki.time = 0
                inp.ki.dwExtraInfo = TOOL_MARKER
                return inp

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

            if not use_unicode_fallback and int(MapVirtualKeyW(vk_code, 0)) & 0xFF:
                seq.append(_mk_key_input(vk_code, is_up=False))
                seq.append(_mk_key_input(vk_code, is_up=True))
            else:
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
            try:
                import keyboard
                keyboard.press_and_release(key_str)
                return True
            except Exception as e2:
                self._ui_log(f"<b style='color:red;'>[Key]</b> Keyboard fallback failed: {e2}")
                return False
