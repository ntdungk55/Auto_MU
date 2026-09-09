"""Game-state event detection."""

from __future__ import annotations

from ..domain.game_event import GameEvent
from ..domain.game_state import GameState


class EventDetector:
    """Convert meaningful state transitions into deduplicated game events."""

    def detect(
        self,
        previous_state: GameState | None,
        current_state: GameState,
    ) -> list[GameEvent]:
        """Detect events after event rules and cooldown storage are implemented."""
        raise NotImplementedError("Game event rules are not implemented yet")
