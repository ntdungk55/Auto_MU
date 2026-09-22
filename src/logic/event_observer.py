"""Pure state machines for registered location events."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any, Callable, Literal


TriggerMode = Literal["enter", "exit", "source_to_destination"]


@dataclass
class LocationState:
    """Validated map and coordinate state from the game."""

    map_name: str
    x: int
    y: int


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
    destination: LocationCondition


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
    destination = condition_from_dict(data.get("destination"))
    if destination is None:
        raise ValueError("event destination is required")
    trigger_mode = str(data.get("trigger_mode", "enter"))
    if trigger_mode not in ("enter", "exit", "source_to_destination"):
        raise ValueError("unsupported event trigger mode")
    return RegisteredEvent(
        event_id=str(data.get("event_id", "") or ""),
        name=str(data.get("name", "") or ""),
        prompt=str(data.get("prompt", "") or ""),
        enabled=bool(data.get("enabled", True)),
        observer_type=str(data.get("observer_type", "location") or "location"),
        trigger_mode=trigger_mode,  # type: ignore[arg-type]
        source=condition_from_dict(data.get("source")),
        destination=destination,
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


class LocationObserverService:
    """Poll a game-state reader and evaluate registered events in order."""

    def __init__(self, reader: Callable[[], dict[str, Any]], target_hwnd: int, on_status: Callable[[str, str], None], on_trigger: Callable[[EventTrigger], None], interval_seconds: float = 1.0) -> None:
        self._reader = reader
        self._target_hwnd = int(target_hwnd)
        self._on_status = on_status
        self._on_trigger = on_trigger
        self._interval_seconds = max(0.1, float(interval_seconds))
        self._events: list[RegisteredEvent] = []
        self._observers: dict[str, LocationEventObserver] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._was_unavailable = False

    def update_events(self, events: list[RegisteredEvent]) -> None:
        """Replace definitions and reset all affected runtime state."""
        self._events = list(events)
        self._observers = {item.event_id: LocationEventObserver(item) for item in self._events}

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
        state = self._parse_state(payload)
        if state is None:
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
            observer = self._observers.setdefault(event.event_id, LocationEventObserver(event))
            result = observer.evaluate(state, game_focused=focused)
            self._on_status(event.event_id, result.status)
            if result.triggered:
                self._on_trigger(EventTrigger(event.event_id, event.prompt, result.status, result.suppressed_by_focus))

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

    def _is_game_focused(self) -> bool:
        try:
            import win32gui
            return int(win32gui.GetForegroundWindow() or 0) == self._target_hwnd
        except Exception:
            return False


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
