"""Windows game-process and window discovery."""

from __future__ import annotations

from ..domain.game_target import GameTarget


class ProcessSelector:
    """List and validate selectable top-level game windows without any UI."""

    def list_targets(self, title_contains: str = "") -> tuple[GameTarget, ...]:
        """Return visible windows, optionally filtered by a title fragment."""
        win32gui, win32process, win32api, win32con = self._windows_modules()
        targets: list[GameTarget] = []
        title_filter = title_contains.casefold()

        def collect(hwnd: int, _: object) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = (win32gui.GetWindowText(hwnd) or "").strip()
            if not title or (title_filter and title_filter not in title.casefold()):
                return True
            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            if not process_id:
                return True
            client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
            if client_right <= client_left or client_bottom <= client_top:
                return True
            process_name = self._process_name(process_id, win32api, win32con, win32process)
            targets.append(
                GameTarget(
                    target_id=f"{process_id}:{hwnd}",
                    hwnd=int(hwnd),
                    process_name=process_name,
                    window_title=title,
                )
            )
            return True

        win32gui.EnumWindows(collect, None)
        return tuple(targets)

    def is_valid(self, target: GameTarget) -> bool:
        """Return whether the target handle is still a visible captureable window."""
        win32gui, _, _, _ = self._windows_modules()
        if not win32gui.IsWindow(target.hwnd) or not win32gui.IsWindowVisible(target.hwnd):
            return False
        left, top, right, bottom = win32gui.GetClientRect(target.hwnd)
        return right > left and bottom > top

    @staticmethod
    def _process_name(process_id: int, win32api: object, win32con: object, win32process: object) -> str:
        process_handle = None
        try:
            flags = win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ
            process_handle = win32api.OpenProcess(flags, False, process_id)
            path = win32process.GetModuleFileNameEx(process_handle, 0)
            return path.rsplit("\\", 1)[-1]
        except Exception:
            return ""
        finally:
            if process_handle is not None:
                win32api.CloseHandle(process_handle)

    @staticmethod
    def _windows_modules() -> tuple[object, object, object, object]:
        try:
            import win32api
            import win32con
            import win32gui
            import win32process
        except ImportError as error:
            raise RuntimeError("Windows process selection requires pywin32") from error
        return win32gui, win32process, win32api, win32con
