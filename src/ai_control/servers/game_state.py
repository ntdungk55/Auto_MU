"""Read-only MCP server for the latest captured game window state."""

from __future__ import annotations

import base64
import copy
from dataclasses import dataclass
import hashlib
import logging
import threading
import time
from typing import Any

import cv2

try:
    from mcp.server import FastMCP
except ImportError:  # MCP 2.x
    from mcp.server import MCPServer as FastMCP

from src.ai_control.current_character_info import (
    _normalize_map,
    _normalize_health,
    _normalize_position,
    _read_taught_health_easyocr,
    _read_taught_hud_text,
)
from src.ai_control.auto_play_control import _config, _state_from_templates
from src.ai_control.companion_switcher import PROJECT_ROOT
from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control.servers.process import resolve_selected_process
from src.logic.teaching_session_matcher import match_teaching_session_against_image


mcp = FastMCP("Auto_MU Game State")
_LOGGER = logging.getLogger("auto_mu.game_state")
STANDARD_GAME_CLIENT_WIDTH = 800
STANDARD_GAME_CLIENT_HEIGHT = 600
WINDOW_STATE_NAMES = (
    "map",
    "position",
    "healthBar",
    "autoState",
    "autoPlayManagement",
    "companionTraining",
)


def _configure_game_state_log() -> None:
    """Write matching diagnostics to a file without polluting MCP stdio."""
    if _LOGGER.handlers:
        return
    log_path = PROJECT_ROOT / "logs" / "game_state.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False


def _log_companion_training_result(result: dict[str, Any]) -> None:
    """Persist each companion Train matching result for diagnosis."""
    message = _companion_training_log_message(result)
    if result.get("state") is None:
        _LOGGER.error(message)
    else:
        _LOGGER.info(message)


def _ensure_standard_game_client_size(hwnd: int) -> None:
    """Keep every Window State capture in the Teaching coordinate system."""
    import win32con
    import win32gui

    client_rect = win32gui.GetClientRect(hwnd)
    client_width = int(client_rect[2] - client_rect[0])
    client_height = int(client_rect[3] - client_rect[1])
    if (client_width, client_height) == (
        STANDARD_GAME_CLIENT_WIDTH,
        STANDARD_GAME_CLIENT_HEIGHT,
    ):
        return

    window_rect = win32gui.GetWindowRect(hwnd)
    outer_width = int(window_rect[2] - window_rect[0])
    outer_height = int(window_rect[3] - window_rect[1])
    border_width = max(0, outer_width - client_width)
    border_height = max(0, outer_height - client_height)
    win32gui.SetWindowPos(
        hwnd,
        None,
        int(window_rect[0]),
        int(window_rect[1]),
        STANDARD_GAME_CLIENT_WIDTH + border_width,
        STANDARD_GAME_CLIENT_HEIGHT + border_height,
        win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
    )
    time.sleep(0.15)

    verified_rect = win32gui.GetClientRect(hwnd)
    verified_size = (
        int(verified_rect[2] - verified_rect[0]),
        int(verified_rect[3] - verified_rect[1]),
    )
    if verified_size != (STANDARD_GAME_CLIENT_WIDTH, STANDARD_GAME_CLIENT_HEIGHT):
        raise RuntimeError(
            "Could not resize selected game client area to "
            f"{STANDARD_GAME_CLIENT_WIDTH}x{STANDARD_GAME_CLIENT_HEIGHT}; "
            f"actual size is {verified_size[0]}x{verified_size[1]}"
        )


def _companion_training_log_message(result: dict[str, Any]) -> str:
    """Format one detailed periodic companion Train matching log line."""
    state = result.get("state")
    session_id = str(result.get("session_id") or "<empty>")
    if state is None:
        return (
            "[Companion Train][ERROR] state=unknown "
            f"session={session_id} capture={result.get('capture_size') or 'N/A'} "
            f"error={result.get('error') or 'Unknown matching error'}"
        )

    score = result.get("score")
    threshold = result.get("threshold")
    score_text = f"{float(score):.3f}" if isinstance(score, (int, float)) else "N/A"
    threshold_text = (
        f"{float(threshold):.3f}"
        if isinstance(threshold, (int, float))
        else "N/A"
    )
    roi = result.get("roi")
    if isinstance(roi, dict):
        roi_text = (
            f"({roi.get('x1')},{roi.get('y1')})-"
            f"({roi.get('x2')},{roi.get('y2')})"
        )
    else:
        roi_text = "N/A"
    capture_size = result.get("capture_size")
    capture_text = (
        f"{capture_size.get('width')}x{capture_size.get('height')}"
        if isinstance(capture_size, dict)
        else "N/A"
    )
    return (
        f"[Companion Train] state={state} score={score_text} "
        f"threshold={threshold_text} session={session_id} roi={roi_text} "
        f"capture={capture_text}"
    )


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
        self._monitor_snapshot: dict[str, Any] | None = None

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

    def replace_monitor_snapshot(self, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._monitor_snapshot = copy.deepcopy(snapshot)

    def read_monitor_snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            return copy.deepcopy(self._monitor_snapshot)


class GameStateService:
    """Capture/OCR state in the background without sending game input."""

    def __init__(self, store: GameStateStore, interval_seconds: float = 2.0) -> None:
        self.store = store
        self.interval_seconds = max(0.1, float(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._roi_cache: dict[tuple[int, str], tuple[bytes, Any, dict[str, Any]]] = {}
        self._configuration_lock = threading.RLock()
        self._enabled_states = set(WINDOW_STATE_NAMES)
        self._pinned_target: dict[str, Any] | None = None

    def configure_states(self, enabled_states: list[str]) -> dict[str, Any]:
        """Apply one chat tab's runtime state selection and pin its game target."""
        requested = {str(name) for name in enabled_states}
        unknown = sorted(requested.difference(WINDOW_STATE_NAMES))
        if unknown:
            raise ValueError(f"Unknown Window State names: {', '.join(unknown)}")
        target = self._selected_target()
        if target is None:
            raise RuntimeError("No unique selected visible game window")
        with self._configuration_lock:
            self._enabled_states = requested
            self._pinned_target = target
        return self.configuration_snapshot()

    def configuration_snapshot(self) -> dict[str, Any]:
        with self._configuration_lock:
            enabled = set(self._enabled_states)
            target = dict(self._pinned_target) if self._pinned_target else None
        return {
            "available_states": list(WINDOW_STATE_NAMES),
            "enabled_states": [name for name in WINDOW_STATE_NAMES if name in enabled],
            "target": target,
        }

    def _runtime_configuration(self) -> tuple[set[str], dict[str, Any] | None]:
        with self._configuration_lock:
            return set(self._enabled_states), (
                dict(self._pinned_target) if self._pinned_target else None
            )

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
            _enabled_states, pinned_target = self._runtime_configuration()
            target = pinned_target or self._selected_target()
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
                if result.get("success"):
                    map_name = str(map_name or "")
                    position = dict(position or {})
                    self.store.replace(GameStateSnapshot(
                        hwnd=int(target["hwnd"]),
                        map=map_name,
                        position={key: int(value) for key, value in position.items() if key in ("x", "y")},
                        main_info=dict(result["main_info"]),
                        captured_at=time.time(),
                        target=target,
                    ))
                else:
                    error_message = str(result.get("error") or "Incomplete game state")
                    if not result.get("enabled_states"):
                        self.store.clear(error_message)
                    else:
                        self.store.set_error(error_message)
                companion_result = (
                    result.get("main_info", {}).get("companionTraining", {})
                    if isinstance(result, dict)
                    else {}
                )
                if companion_result:
                    _log_companion_training_result(companion_result)
            self._stop.wait(self.interval_seconds)

    def _read_window_state(self, target: dict[str, Any]) -> dict[str, Any]:
        """Capture once and read all non-dialog HUD state from that image."""
        import win32gui

        hwnd = int(target["hwnd"])
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            raise RuntimeError("Selected game window is no longer visible")
        config = _config()
        _ensure_standard_game_client_size(hwnd)
        image = GameWindowCapture().capture(hwnd)
        if image is None:
            raise RuntimeError("Could not capture the selected game window")
        enabled_states, _pinned_target = self._runtime_configuration()
        main_info = config["mainInfo"]
        values: dict[str, Any] = {}
        state_results: dict[str, dict[str, Any]] = {}

        text_readers = {
            "map": (_normalize_map, _read_taught_hud_text),
            "position": (_normalize_position, _read_taught_hud_text),
            "healthBar": (_normalize_health, _read_taught_health_easyocr),
        }
        for name, (normalizer, reader) in text_readers.items():
            if name not in enabled_states:
                continue
            try:
                value, evidence = self._read_cached_roi(
                    hwnd, image, name, main_info[name], normalizer, reader,
                )
                values[name] = value
                state_results[name] = dict(evidence)
            except Exception as error:
                state_results[name] = {"error": str(error), "roi": main_info[name].get("roi")}

        for name in ("autoState", "autoPlayManagement"):
            if name not in enabled_states:
                continue
            control = main_info[name]
            try:
                state_results[name] = _state_from_templates(
                    image,
                    control["roi"],
                    control["stateTemplates"],
                    icon_roi_relative=control.get("iconRoiRelative"),
                    edge_matching=bool(control.get("edgeMatching", False)),
                    threshold_override=control.get("edgeThreshold"),
                )
            except Exception as error:
                state_results[name] = {"error": str(error), "roi": control.get("roi")}

        if "companionTraining" in enabled_states:
            companion = main_info["companionManagement1"]
            state_results["companionTraining"] = self._companion_training_state(image, companion)

        monitor_states = self._build_monitor_states(
            main_info, enabled_states, values, state_results
        )
        encoded_ok, encoded_image = cv2.imencode(
            ".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 82]
        )
        if not encoded_ok:
            raise RuntimeError("Could not encode Window State monitor image")
        self.store.replace_monitor_snapshot({
            "success": True,
            "hwnd": hwnd,
            "captured_at": time.time(),
            "image_width": int(image.shape[1]),
            "image_height": int(image.shape[0]),
            "image_jpeg_base64": base64.b64encode(encoded_image.tobytes()).decode("ascii"),
            "states": monitor_states,
            "enabled_states": [name for name in WINDOW_STATE_NAMES if name in enabled_states],
        })

        successful_states = [
            name for name, result in state_results.items()
            if not result.get("error") and (
                values.get(name) is not None
                if name in text_readers
                else result.get("state") is not None
            )
        ]
        return {
            "success": bool(successful_states),
            "error": None if successful_states else "No enabled Window State produced a result",
            "map": values.get("map"),
            "position": values.get("position"),
            "enabled_states": [name for name in WINDOW_STATE_NAMES if name in enabled_states],
            "main_info": {
                **{
                    name: {"value": values.get(name), "ocr": state_results.get(name, {})}
                    for name in text_readers if name in enabled_states
                },
                **{
                    name: state_results[name]
                    for name in ("autoState", "autoPlayManagement", "companionTraining")
                    if name in state_results
                },
            },
        }

    @staticmethod
    def _build_monitor_states(
        main_info: dict[str, Any],
        enabled_states: set[str],
        values: dict[str, Any],
        results: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Describe every state overlay without exposing preprocessed images."""
        states: list[dict[str, Any]] = []
        for name in WINDOW_STATE_NAMES:
            definition_name = "companionManagement1" if name == "companionTraining" else name
            definition = dict(main_info.get(definition_name, {}))
            result = dict(results.get(name, {}))
            roi = result.get("roi") or definition.get("roi")
            masks = (
                result.get("masks")
                or definition.get("mask_regions")
                or definition.get("maskRegions")
                or []
            )
            value = values.get(name)
            confidence = result.get("confidence")
            if name in ("autoState", "autoPlayManagement"):
                value = result.get("state")
                scores = result.get("scores") or {}
                confidence = scores.get(value) if value else None
            elif name == "companionTraining":
                value = result.get("state")
                confidence = result.get("score")
            states.append({
                "name": name,
                "enabled": name in enabled_states,
                "roi": roi,
                "masks": GameStateService._absolute_monitor_masks(masks, roi),
                "result": value,
                "confidence": confidence,
                "error": result.get("error"),
            })
        return states

    @staticmethod
    def _absolute_monitor_masks(masks: Any, roi: Any) -> list[dict[str, Any]]:
        """Map template-relative x/y/w/h masks onto full-window coordinates."""
        if not isinstance(masks, list):
            return []
        roi_left = int(roi.get("x1", 0)) if isinstance(roi, dict) else 0
        roi_top = int(roi.get("y1", 0)) if isinstance(roi, dict) else 0
        normalized: list[dict[str, Any]] = []
        for mask in masks:
            if not isinstance(mask, dict):
                continue
            if all(key in mask for key in ("x1", "y1", "x2", "y2")):
                normalized.append({key: int(mask[key]) for key in ("x1", "y1", "x2", "y2")})
                continue
            if all(key in mask for key in ("x", "y", "w", "h")):
                normalized.append({
                    "x": roi_left + int(mask["x"]),
                    "y": roi_top + int(mask["y"]),
                    "w": int(mask["w"]),
                    "h": int(mask["h"]),
                })
        return normalized

    @staticmethod
    def _companion_training_state(image: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Return binary Train state using the referenced Teaching session."""
        session_id = str(config.get("trainingTeachingSessionId") or "").strip()
        try:
            result = match_teaching_session_against_image(
                image,
                project_root=PROJECT_ROOT,
                session_id=session_id,
            )
            return {
                "state": "training" if result["matched"] else "not_training",
                "capture_size": {
                    "width": int(image.shape[1]),
                    "height": int(image.shape[0]),
                },
                **result,
            }
        except Exception as error:
            return {
                "state": None,
                "session_id": session_id,
                "capture_size": {
                    "width": int(image.shape[1]),
                    "height": int(image.shape[0]),
                },
                "error": str(error),
            }

    def _read_cached_roi(
        self,
        hwnd: int,
        image: Any,
        name: str,
        definition: dict[str, Any],
        normalizer: Any,
        reader: Any,
    ) -> tuple[Any, dict[str, Any]]:
        """Reuse OCR for an unchanged taught ROI within the same game window."""
        roi = {axis: int(value) for axis, value in dict(definition["roi"]).items()}
        if not (0 <= roi["x1"] < roi["x2"] <= image.shape[1] and 0 <= roi["y1"] < roi["y2"] <= image.shape[0]):
            raise ValueError(f"Current HUD ROI lies outside the captured image: {roi}")
        crop = image[roi["y1"]:roi["y2"], roi["x1"]:roi["x2"]]
        fingerprint = hashlib.blake2b(crop.tobytes(), digest_size=8).digest()
        key = (int(hwnd), name)
        cached = self._roi_cache.get(key)
        if cached is not None and cached[0] == fingerprint:
            return cached[1], cached[2]
        value, evidence = reader(image, definition, normalizer)
        self._roi_cache[key] = (fingerprint, value, evidence)
        return value, evidence


_store = GameStateStore()
_service = GameStateService(_store)


@mcp.tool()
def configure_window_states(enabled_states: list[str]) -> dict[str, Any]:
    """Enable or disable the actual Window States consumed by this AI Chat tab."""
    configuration = _service.configure_states(list(enabled_states or []))
    return {"success": True, **configuration}


@mcp.tool()
def get_window_state_monitor_snapshot() -> dict[str, Any]:
    """Return the latest original capture plus ROI/mask/result overlay metadata."""
    snapshot = _store.read_monitor_snapshot()
    configuration = _service.configuration_snapshot()
    if snapshot is None:
        return {
            "success": False,
            "error": "Window State has not captured an image yet",
            **configuration,
        }
    return {**snapshot, **configuration}


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
    if not result.get("map") or not isinstance(result.get("position"), dict):
        return {
            "success": False,
            "error": "Map/position Window States are disabled or unavailable",
        }
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
    state = result["state"].get("main_info", {}).get("companionTraining")
    if not isinstance(state, dict):
        return {
            "success": False,
            "error": "companionTraining Window State is disabled or unavailable",
        }
    return {
        "success": state.get("state") is not None,
        "target": result["state"]["target"],
        **state,
        "captured_at": result["captured_at"],
    }


def run_game_state_mcp_server() -> None:
    """Run the state server and its capture worker over stdio."""
    _configure_game_state_log()
    _service.start()
    try:
        mcp.run(transport="stdio")
    finally:
        _service.stop()
