"""Scenario lifecycle orchestrator."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock

from ..domain.game_event import GameEvent
EventListener = Callable[[GameEvent], None]


class ScenarioEngine:
    """Own the event-listener boundary before AI execution is introduced."""

    def __init__(self) -> None:
        self._listeners: set[EventListener] = set()
        self._lock = RLock()

    def subscribe(self, listener: EventListener) -> None:
        """Register one caller that wants to receive future game events."""
        with self._lock:
            self._listeners.add(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        """Remove one event listener without affecting other listeners."""
        with self._lock:
            self._listeners.discard(listener)

    def publish(self, events: list[GameEvent]) -> None:
        """Deliver detected events while isolating listener failures."""
        if not events:
            return
        with self._lock:
            listeners = tuple(self._listeners)
        for event in events:
            for listener in listeners:
                try:
                    listener(event)
                except Exception:
                    continue
