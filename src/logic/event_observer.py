"""Pure state machines for registered location events."""

from __future__ import annotations

from dataclasses import dataclass
import re
import threading
import time
from typing import Any, Callable, Literal


TriggerMode = Literal["enter", "exit", "source_to_destination", "health_below"]


@dataclass
class LocationState:
    """Validated map and coordinate state from the game."""

    map_name: str
    x: int
    y: int


@dataclass
class HealthState:
    """Validated current health read from the game HUD."""

    current: int


def is_health_below_transition(
    previous: HealthState | None,
    current: HealthState | None,
    threshold: int = 100,
) -> bool:
    """Return the exact transition used by the Window State health logger."""
    return (
        previous is not None
        and current is not None
        and previous.current >= int(threshold)
        and current.current < int(threshold)
    )


@dataclass
class LocationCondition:
    """Map condition with an optional inclusive coordinate rectangle."""

    map_id: int
    map_name: str
    use_coordinates: bool = False
    min_x: int | None = None
    max_x: int | None = None
    min_y: int | None = None
    max_y: int | None = None

    def matches(self, state: LocationState | None) -> bool:
        """Return whether a complete state is inside this condition."""
        if state is None or self.map_name.strip().casefold() != state.map_name.strip().casefold():
            return False
        if not self.use_coordinates:
            return True
        if None in (self.min_x, self.max_x, self.min_y, self.max_y):
            return False
        return self.min_x <= state.x <= self.max_x and self.min_y <= state.y <= self.max_y


@dataclass
class RegisteredEvent:
    """Persisted event definition consumed by the observer."""

    event_id: str
    name: str
    prompt: str
    enabled: bool
    observer_type: str
    trigger_mode: TriggerMode
    source: LocationCondition | None
    destination: LocationCondition | None
    health_threshold: int = 100


def condition_from_dict(data: dict[str, Any] | None) -> LocationCondition | None:
    """Build a location condition from persisted data."""
    if not isinstance(data, dict):
        return None
    return LocationCondition(
        map_id=int(data.get("map_id", 0) or 0),
        map_name=str(data.get("map_name", "") or ""),
        use_coordinates=bool(data.get("use_coordinates", False)),
        min_x=data.get("min_x"),
        max_x=data.get("max_x"),
        min_y=data.get("min_y"),
        max_y=data.get("max_y"),
    )


def registered_event_from_dict(data: dict[str, Any]) -> RegisteredEvent:
    """Build an observer event from persistence data."""
    observer_type = str(data.get("observer_type", "location") or "location")
    destination = condition_from_dict(data.get("destination"))
    if observer_type == "location" and destination is None:
        raise ValueError("event destination is required")
    trigger_mode = str(data.get("trigger_mode", "enter"))
    if observer_type == "health":
        trigger_mode = "health_below"
    elif trigger_mode not in ("enter", "exit", "source_to_destination"):
        raise ValueError("unsupported event trigger mode")
    return RegisteredEvent(
        event_id=str(data.get("event_id", "") or ""),
        name=str(data.get("name", "") or ""),
        prompt=str(data.get("prompt", "") or ""),
        enabled=bool(data.get("enabled", True)),
        observer_type=observer_type,
        trigger_mode=trigger_mode,  # type: ignore[arg-type]
        source=condition_from_dict(data.get("source")),
        destination=destination,
        health_threshold=max(0, int(data.get("health_threshold", 100) or 0)),
    )


@dataclass(frozen=True)
class ObserverResult:
    """Result of evaluating one state sample."""

    triggered: bool
    status: str
    suppressed_by_focus: bool = False


@dataclass(frozen=True)
class EventTrigger:
    """Event notification emitted by the polling service."""

    event_id: str
    prompt: str
    status: str
    suppressed_by_focus: bool
    observer_type: str = "location"
    character_name: str = "Game"
    details: dict[str, Any] | None = None


class LocationObserverService:
    """Poll a game-state reader and evaluate registered events in order."""

    def __init__(self, reader: Callable[[], dict[str, Any]], target_hwnd: int, on_status: Callable[[str, str], None], on_trigger: Callable[[EventTrigger], None], interval_seconds: float = 1.0) -> None:
        self._reader = reader
        self._target_hwnd = int(target_hwnd)
        self._on_status = on_status
        self._on_trigger = on_trigger
        self._interval_seconds = max(0.1, float(interval_seconds))
        self._events: list[RegisteredEvent] = []
        self._observers: dict[str, Any] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._was_unavailable = False

    def update_events(self, events: list[RegisteredEvent]) -> None:
        """Replace definitions and reset all affected runtime state."""
        self._events = list(events)
        self._observers = {item.event_id: self._make_observer(item) for item in self._events}

    def start(self) -> None:
        """Start the polling thread once."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="location-event-observer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop polling and wait briefly for the worker to exit."""
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
        self._thread = None

    def reset(self) -> None:
        """Reset every event runtime state."""
        for observer in self._observers.values():
            observer.reset()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._poll_once()
            self._stop.wait(self._interval_seconds)

    def _poll_once(self) -> None:
        try:
            payload = self._reader()
        except Exception as error:
            self._on_status("__service__", f"MCP error: {error}")
            self._handle_unavailable()
            return
        location_state = self._parse_state(payload)
        health_state = self._parse_health_state(payload)
        previous_location = self._parse_previous_state(payload)
        previous_health = self._parse_previous_health_state(payload)
        if any(item.enabled and item.observer_type == "health" for item in self._events):
            print(
                "[Health Observer] "
                f"character={self._character_name(payload)} "
                f"previous_hp={previous_health.current if previous_health is not None else None} "
                f"current_hp={health_state.current if health_state is not None else None}",
                flush=True,
            )
        if location_state is None and health_state is None:
            self._handle_unavailable()
            return
        if self._was_unavailable:
            self.reset()
            self._was_unavailable = False
        focused = self._is_game_focused()
        for event in self._events:
            if not event.enabled:
                self._on_status(event.event_id, "Disabled")
                continue
            observer = self._observers.setdefault(event.event_id, self._make_observer(event))
            state = health_state if event.observer_type == "health" else location_state
            previous = previous_health if event.observer_type == "health" else previous_location
            if event.observer_type == "health":
                result = observer.evaluate_window_pair(
                    previous_state=previous,
                    current_state=state,
                    current_captured_at=payload.get("captured_at") if isinstance(payload, dict) else None,
                    game_focused=focused,
                )
            else:
                result = observer.evaluate(state, game_focused=focused)
            self._on_status(event.event_id, result.status)
            if result.triggered:
                self._on_trigger(EventTrigger(
                    event.event_id,
                    event.prompt,
                    result.status,
                    result.suppressed_by_focus,
                    event.observer_type,
                    self._character_name(payload),
                    self._trigger_details(location_state, health_state),
                ))

    def _handle_unavailable(self) -> None:
        try:
            import win32gui
            unavailable = not win32gui.IsWindowVisible(self._target_hwnd)
        except Exception:
            unavailable = False
        if unavailable:
            self.reset()
            self._was_unavailable = True
        self._on_status("__service__", "Waiting for valid game state")

    @staticmethod
    def _parse_state(payload: dict[str, Any] | None) -> LocationState | None:
        if not isinstance(payload, dict) or not bool(payload.get("success")):
            return None
        position = payload.get("position")
        if not isinstance(position, dict) or position.get("x") is None or position.get("y") is None or not payload.get("map"):
            return None
        return LocationState(str(payload["map"]), int(position["x"]), int(position["y"]))

    @staticmethod
    def _parse_health_state(payload: dict[str, Any] | None) -> HealthState | None:
        if not isinstance(payload, dict) or not bool(payload.get("success")):
            return None
        state = payload.get("state")
        main_info = state.get("main_info", {}) if isinstance(state, dict) else {}
        health_entry = main_info.get("healthBar") if isinstance(main_info, dict) else None
        value = health_entry.get("value") if isinstance(health_entry, dict) else None
        if value is None and isinstance(health_entry, dict):
            value = health_entry
        if not isinstance(value, dict) or value.get("current") is None:
            return None
        try:
            return HealthState(int(value["current"]))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _parse_previous_state(cls, payload: dict[str, Any] | None) -> LocationState | None:
        if not isinstance(payload, dict):
            return None
        previous = payload.get("previous_state")
        if not isinstance(previous, dict):
            return None
        return cls._parse_state({"success": True, "map": previous.get("map"), "position": previous.get("position")})

    @staticmethod
    def _parse_previous_health_state(payload: dict[str, Any] | None) -> HealthState | None:
        if not isinstance(payload, dict) or not isinstance(payload.get("previous_state"), dict):
            return None
        previous = payload["previous_state"]
        main_info = previous.get("main_info", {})
        health_entry = main_info.get("healthBar") if isinstance(main_info, dict) else None
        value = health_entry.get("value") if isinstance(health_entry, dict) else None
        if value is None and isinstance(health_entry, dict):
            value = health_entry
        if not isinstance(value, dict) or value.get("current") is None:
            return None
        try:
            return HealthState(int(value["current"]))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _make_observer(event: RegisteredEvent) -> Any:
        return HealthEventObserver(event) if event.observer_type == "health" else LocationEventObserver(event)

    @staticmethod
    def _character_name(payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return "Game"
        state = payload.get("state")
        if not isinstance(state, dict):
            state = {}
        target = state.get("target")
        if not isinstance(target, dict):
            target = {}
        title = str(target.get("title", "") or "") if isinstance(target, dict) else ""
        match = re.search(r"\([^)]*-\s*([^)]+)\)", title)
        return match.group(1).strip() if match else (title.strip() or "Game")

    @staticmethod
    def _trigger_details(location: LocationState | None, health: HealthState | None) -> dict[str, Any]:
        details: dict[str, Any] = {}
        if location is not None:
            details.update({"map": location.map_name, "x": location.x, "y": location.y})
        if health is not None:
            details.update({
                "current_hp": health.current,
                "dead": health.current <= 0,
            })
        return details

    def _is_game_focused(self) -> bool:
        try:
            import win32gui
            return int(win32gui.GetForegroundWindow() or 0) == self._target_hwnd
        except Exception:
            return False


class HealthEventObserver:
    """Apply the health rule directly to Window State previous/current values."""

    def __init__(self, event: RegisteredEvent) -> None:
        self.event = event
        self._last_trigger_captured_at: float | None = None
        self._armed = True
        self._status = "Waiting for initial state"

    def reset(self) -> None:
        self._last_trigger_captured_at = None
        self._armed = True
        self._status = "Waiting for initial state"

    def evaluate_window_pair(
        self,
        *,
        previous_state: HealthState | None,
        current_state: HealthState | None,
        current_captured_at: Any = None,
        game_focused: bool,
    ) -> ObserverResult:
        if previous_state is None or current_state is None:
            return ObserverResult(False, "Waiting for valid health state")
        threshold = self.event.health_threshold
        if current_state.current >= threshold:
            self._armed = True
            self._status = f"HP normal ({current_state.current})"
            return ObserverResult(False, self._status)
        if self._armed and is_health_below_transition(previous_state, current_state, threshold):
            captured_at = float(current_captured_at) if current_captured_at is not None else None
            if captured_at is not None and captured_at == self._last_trigger_captured_at:
                return ObserverResult(False, self._status)
            self._last_trigger_captured_at = captured_at
            self._armed = False
            if game_focused:
                self._status = "Ignored: game focused"
                return ObserverResult(True, self._status, suppressed_by_focus=True)
            self._status = f"HP below {threshold} ({current_state.current})"
            return ObserverResult(True, self._status)
        self._status = f"HP below {threshold} ({current_state.current})"
        return ObserverResult(False, self._status)


class LocationEventObserver:
    """Evaluate one registered event against sequential location states."""

    def __init__(self, event: RegisteredEvent) -> None:
        self.event = event
        self._baseline_ready = False
        self._previous_state: LocationState | None = None
        self._source_matched = False
        self._armed = True
        self._status = "Waiting for initial state"

    def reset(self) -> None:
        """Reset runtime state and require a new baseline."""
        self._baseline_ready = False
        self._previous_state = None
        self._source_matched = False
        self._armed = True
        self._status = "Waiting for initial state"

    def prime(self, state: LocationState | None) -> None:
        """Use Window State's previous sample as the initial comparison point."""
        if not self._baseline_ready and state is not None:
            self._baseline_ready = True
            self._previous_state = state

    def evaluate(self, state: LocationState | None, *, game_focused: bool) -> ObserverResult:
        """Evaluate one sample without mutating state for invalid samples."""
        if state is None:
            return ObserverResult(False, self._status)
        if not self._baseline_ready:
            self._baseline_ready = True
            self._previous_state = state
            self._status = "Waiting for initial state"
            return ObserverResult(False, self._status)

        result = self._evaluate_transition(state)
        self._previous_state = state
        if not result.triggered:
            return result
        if game_focused:
            self._status = "Ignored: game focused"
            return ObserverResult(True, self._status, suppressed_by_focus=True)
        self._status = result.status
        return result

    def _initial_status(self, state: LocationState) -> str:
        if self.event.trigger_mode == "source_to_destination":
            return "Waiting source"
        return "Inside destination" if self.event.destination.matches(state) else "Outside destination"

    def _evaluate_transition(self, state: LocationState) -> ObserverResult:
        previous = self._previous_state
        if previous is None:
            return ObserverResult(False, self._status)
        if self.event.trigger_mode == "enter":
            return self._evaluate_enter(previous, state)
        if self.event.trigger_mode == "exit":
            return self._evaluate_exit(previous, state)
        return self._evaluate_source_to_destination(state)

    def _evaluate_enter(self, previous: LocationState, current: LocationState) -> ObserverResult:
        was_inside = self.event.destination.matches(previous)
        is_inside = self.event.destination.matches(current)
        if not is_inside:
            self._armed = True
            self._status = "Outside destination"
            return ObserverResult(False, self._status)
        if self._armed and not was_inside:
            self._armed = False
            return ObserverResult(True, "Destination matched")
        self._status = "Inside destination"
        return ObserverResult(False, self._status)

    def _evaluate_exit(self, previous: LocationState, current: LocationState) -> ObserverResult:
        was_inside = self.event.destination.matches(previous)
        is_inside = self.event.destination.matches(current)
        if is_inside:
            self._armed = True
            self._status = "Inside destination"
            return ObserverResult(False, self._status)
        if self._armed and was_inside:
            self._armed = False
            return ObserverResult(True, "Destination exited")
        self._status = "Outside destination"
        return ObserverResult(False, self._status)

    def _evaluate_source_to_destination(self, state: LocationState) -> ObserverResult:
        source = self.event.source
        if source is None:
            self._source_matched = False
            self._status = "Waiting source"
            return ObserverResult(False, self._status)
        if not self._source_matched:
            if source.matches(state):
                self._source_matched = True
                self._status = "Source matched"
            else:
                self._status = "Waiting source"
            return ObserverResult(False, self._status)
        if self.event.destination.matches(state):
            self._source_matched = False
            return ObserverResult(True, "Destination matched")
        if not source.matches(state):
            self._source_matched = False
            self._status = "Waiting source"
        else:
            self._status = "Source matched"
        return ObserverResult(False, self._status)
