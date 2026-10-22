"""Latest game-state storage."""

from __future__ import annotations

from threading import RLock

from ..domain.game_state import GameState


class GameStateStore:
    """Keep the latest immutable state snapshot for each game target."""

    def __init__(self) -> None:
        self._states: dict[str, GameState] = {}
        self._lock = RLock()

    def put(self, state: GameState) -> None:
        """Replace the latest state for one target."""
        with self._lock:
            self._states[state.target_id] = state

    def get(self, target_id: str) -> GameState | None:
        """Return the latest state for one target."""
        with self._lock:
            return self._states.get(target_id)

    def get_all(self) -> tuple[GameState, ...]:
        """Return a stable snapshot of every currently known target."""
        with self._lock:
            return tuple(self._states.values())
