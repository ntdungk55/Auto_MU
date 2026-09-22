"""Read-only MCP server for the latest captured game window state."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any

try:
    from mcp.server import FastMCP
except ImportError:  # MCP 2.x
    from mcp.server import MCPServer as FastMCP

from src.ai_control.current_character_info import (
    _normalize_map,
    _normalize_position,
    _read_taught_hud_text,
)
from src.ai_control.auto_play_control import _config, _state_from_templates
from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control.servers.process import resolve_selected_process


mcp = FastMCP("Auto_MU Game State")


@dataclass(frozen=True)
class GameStateSnapshot:
    """One immutable state returned by the read-only capture worker."""

    hwnd: int
    map: str
    position: dict[str, int]
    captured_at: float
    target: dict[str, Any]
    main_info: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "hwnd": self.hwnd,
            "map": self.map,
            "position": dict(self.position),
            "main_info": dict(self.main_info or {}),
            "captured_at": self.captured_at,
            "target": dict(self.target),
        }


class GameStateStore:
    """Thread-safe previous/current state store owned by the MCP server."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._previous: GameStateSnapshot | None = None
        self._current: GameStateSnapshot | None = None
        self._error: str | None = None

    def replace(self, snapshot: GameStateSnapshot) -> None:
        with self._lock:
            if self._current is not None and self._current.hwnd == snapshot.hwnd:
                self._previous = self._current
            else:
                self._previous = None
            self._current = snapshot
            self._error = None

    def clear(self, error: str) -> None:
        with self._lock:
            self._previous = None
            self._current = None
            self._error = str(error)

    def set_error(self, error: str) -> None:
        """Retain valid states while recording a temporary read failure."""
        with self._lock:
            self._error = str(error)

    def read(self) -> tuple[GameStateSnapshot | None, GameStateSnapshot | None, str | None]:
        with self._lock:
            return self._previous, self._current, self._error


class GameStateService:
    """Capture/OCR state in the background without sending game input."""

    def __init__(self, store: GameStateStore, interval_seconds: float = 0.5) -> None:
        self.store = store
        self.interval_seconds = max(0.1, float(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="game-state-capture", daemon=True)
        self._thread.start()

    def stop(self, timeout_seconds: float = 3.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(max(0.1, float(timeout_seconds)))
        self._thread = None

    @staticmethod
    def _selected_target() -> dict[str, Any] | None:
        process, error = resolve_selected_process()
        if error or not process:
            return None
        selected_hwnd = int(process.get("selected_window_hwnd") or 0)
        windows = [window for window in process.get("windows", []) if window.get("visible")]
        if selected_hwnd:
            windows = [window for window in windows if int(window.get("hwnd", 0)) == selected_hwnd]
        if len(windows) != 1:
            return None
        return dict(windows[0])

    def _run(self) -> None:
        while not self._stop.is_set():
            target = self._selected_target()
            if target is None:
                self.store.clear("No unique selected visible game window")
            else:
                try:
                    result = self._read_window_state(target)
                except Exception as error:
                    self.store.set_error(str(error))
                    self._stop.wait(self.interval_seconds)
                    continue
                position = result.get("position")
                map_name = result.get("map")
                if result.get("success") and isinstance(map_name, str) and isinstance(position, dict):
                    self.store.replace(GameStateSnapshot(
                        hwnd=int(target["hwnd"]),
                        map=map_name,
                        position={"x": int(position["x"]), "y": int(position["y"])},
                        main_info=dict(result["main_info"]),
                        captured_at=time.time(),
                        target=target,
                    ))
                else:
                    self.store.set_error(str(result.get("error") or "Incomplete game state"))
            self._stop.wait(self.interval_seconds)

    @staticmethod
    def _read_window_state(target: dict[str, Any]) -> dict[str, Any]:
        """Capture once and read all non-dialog HUD state from that image."""
        import win32gui

        hwnd = int(target["hwnd"])
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            raise RuntimeError("Selected game window is no longer visible")
        config = _config()
        image = GameWindowCapture().capture(hwnd)
        if image is None:
            raise RuntimeError("Could not capture the selected game window")
        main_info = config["mainInfo"]
        map_value, map_ocr = _read_taught_hud_text(image, main_info["map"], _normalize_map)
        position_value, position_ocr = _read_taught_hud_text(
            image, main_info["position"], _normalize_position,
        )
        if map_value is None or position_value is None:
            raise RuntimeError("Could not read complete map/position state")

        image_states: dict[str, Any] = {}
        for name in ("autoState", "autoPlayManagement"):
            control = main_info[name]
            image_states[name] = _state_from_templates(
                image,
                control["roi"],
                control["stateTemplates"],
                icon_roi_relative=control.get("iconRoiRelative"),
                edge_matching=bool(control.get("edgeMatching", False)),
                threshold_override=control.get("edgeThreshold"),
            )
        companion = main_info["companionManagement1"]
        image_states["companionTraining"] = _state_from_templates(
            image,
            companion["roi"],
            companion["trainingStateTemplates"],
            icon_roi_relative=companion.get("trainingIconRoiRelative"),
            edge_matching=bool(companion.get("edgeMatching", False)),
            threshold_override=companion.get("edgeThreshold"),
        )
        return {
            "success": True,
            "map": map_value,
            "position": position_value,
            "main_info": {
                "map": {"value": map_value, "ocr": map_ocr},
                "position": {"value": position_value, "ocr": position_ocr},
                "autoState": image_states["autoState"],
                "autoPlayManagement": image_states["autoPlayManagement"],
                "companionTraining": image_states["companionTraining"],
            },
        }


_store = GameStateStore()
_service = GameStateService(_store)


@mcp.tool()
def get_selected_game_state(include_previous: bool = False) -> dict[str, Any]:
    """Return the latest complete captured state, optionally with its predecessor."""
    previous, current, error = _store.read()
    if current is None:
        return {"success": False, "state": None, "error": error or "Game state unavailable"}
    payload = current.as_dict()
    result: dict[str, Any] = {
        "success": True,
        "state": payload,
        "map": payload["map"],
        "position": payload["position"],
        "captured_at": payload["captured_at"],
    }
    if include_previous:
        result["previous_state"] = previous.as_dict() if previous is not None else None
    return result


@mcp.tool()
def get_current_character_map() -> dict[str, Any]:
    """Read map and coordinates from the latest Window State snapshot."""
    result = get_selected_game_state()
    if not result.get("success"):
        return result
    return {
        "success": True,
        "target": result["state"]["target"],
        "map": result["map"],
        "position": result["position"],
        "captured_at": result["captured_at"],
    }


@mcp.tool()
def get_companion_training_state() -> dict[str, Any]:
    """Read companion training state from the latest Window State snapshot."""
    result = get_selected_game_state()
    if not result.get("success"):
        return result
    state = result["state"]["main_info"]["companionTraining"]
    return {
        "success": state.get("state") is not None,
        "target": result["state"]["target"],
        **state,
        "captured_at": result["captured_at"],
    }


def run_game_state_mcp_server() -> None:
    """Run the state server and its capture worker over stdio."""
    _service.start()
    try:
        mcp.run(transport="stdio")
    finally:
        _service.stop()
