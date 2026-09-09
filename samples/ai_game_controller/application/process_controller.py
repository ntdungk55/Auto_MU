"""Sample process lifecycle controller."""

from __future__ import annotations

from threading import Event, RLock, Thread
from time import monotonic

from ..domain.game_target import GameTarget
from ..domain.scenario import Scenario
from ..infrastructure.game_state_reader import GameStateReader
from ..infrastructure.game_state_store import GameStateStore
from ..infrastructure.process_selector import ProcessSelector
from .event_detector import EventDetector
from .scenario_engine import AIResponseListener, EventListener, ScenarioEngine


class AIProcessController:
    """Run the selected game-state pipeline without depending on any UI."""

    def __init__(
        self,
        game_state_reader: GameStateReader,
        game_state_store: GameStateStore,
        event_detector: EventDetector,
        scenario_engine: ScenarioEngine,
        process_selector: ProcessSelector | None = None,
        interval_ms: int = 500,
    ) -> None:
        self.game_state_reader = game_state_reader
        self.game_state_store = game_state_store
        self.event_detector = event_detector
        self.scenario_engine = scenario_engine
        self.process_selector = process_selector
        self.interval_ms = max(1, interval_ms)
        self.is_running = False
        self.last_error: str | None = None
        self._target: GameTarget | None = None
        self._scenario: Scenario | None = None
        self._stop_event = Event()
        self._worker: Thread | None = None
        self._lock = RLock()

    @property
    def target(self) -> GameTarget | None:
        """Return the configured target without exposing mutable runtime data."""
        with self._lock:
            return self._target

    def list_targets(self, title_contains: str = "") -> tuple[GameTarget, ...]:
        """List selectable Windows game targets for a future caller UI."""
        if self.process_selector is None:
            return ()
        return self.process_selector.list_targets(title_contains)

    def select_target(self, target: GameTarget) -> None:
        """Configure the target used by the next start operation."""
        with self._lock:
            if self.is_running:
                raise RuntimeError("cannot change target while the controller is running")
            self._target = target

    def select_scenario(self, scenario: Scenario) -> None:
        """Configure the immutable scenario snapshot used by the next run."""
        with self._lock:
            if self.is_running:
                raise RuntimeError("cannot change scenario while the controller is running")
            if self._target is not None and scenario.target_id != self._target.target_id:
                raise ValueError("scenario target_id does not match the selected target")
            self._scenario = scenario

    def subscribe(self, listener: EventListener) -> None:
        """Register a future event listener, such as a Gemini Chat bridge."""
        self.scenario_engine.subscribe(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        """Remove a previously registered event listener."""
        self.scenario_engine.unsubscribe(listener)

    def subscribe_ai_response(self, listener: AIResponseListener) -> None:
        """Register a future listener for AI responses derived from game events."""
        self.scenario_engine.subscribe_response(listener)

    def unsubscribe_ai_response(self, listener: AIResponseListener) -> None:
        """Remove one AI-response listener."""
        self.scenario_engine.unsubscribe_response(listener)

    def start(self) -> None:
        """Start one reader worker for the selected target."""
        with self._lock:
            if self.is_running:
                return
            if self._target is None:
                raise RuntimeError("a game target must be selected before start")
            if self.process_selector is not None and not self.process_selector.is_valid(self._target):
                raise RuntimeError("the selected game target is no longer valid")
            self.last_error = None
            self._stop_event.clear()
            self.is_running = True
            self._worker = Thread(target=self._run, name="ai-game-state-reader", daemon=True)
            self._worker.start()

    def stop(self, timeout_seconds: float = 5.0) -> bool:
        """Stop the reader worker and report whether it terminated in time."""
        with self._lock:
            worker = self._worker
            if not self.is_running or worker is None:
                return True
            self._stop_event.set()
        worker.join(timeout=max(0.0, timeout_seconds))
        with self._lock:
            finished = not worker.is_alive()
            if finished:
                self.is_running = False
                self._worker = None
            else:
                self.last_error = "reader worker did not stop before timeout"
            return finished

    def _run(self) -> None:
        """Read, store, detect, and publish states until cancellation is requested."""
        try:
            while not self._stop_event.is_set():
                started_at = monotonic()
                target = self.target
                if target is None:
                    break
                state = self.game_state_reader.read(target)
                if state is not None:
                    previous_state = self.game_state_store.get(state.target_id)
                    self.game_state_store.put(state)
                    with self._lock:
                        scenario = self._scenario
                    self.scenario_engine.handle_events(
                        scenario,
                        self.event_detector.detect(previous_state, state),
                    )
                elif self.game_state_reader.last_error:
                    self.last_error = self.game_state_reader.last_error
                elapsed_ms = (monotonic() - started_at) * 1000
                delay_seconds = max(0.0, (self.interval_ms - elapsed_ms) / 1000)
                self._stop_event.wait(delay_seconds)
        except Exception as error:
            self.last_error = str(error)
        finally:
            with self._lock:
                self.is_running = False
                self._worker = None


ProcessController = AIProcessController
