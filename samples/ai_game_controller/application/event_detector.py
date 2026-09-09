"""Game-state event detection."""

from __future__ import annotations

from ..domain.game_event import GameEvent
from ..domain.game_state import GameState


class EventDetector:
    """Convert meaningful state transitions into game events.

    Event rules are intentionally deferred. The detector therefore preserves the
    future contract while producing no events in this phase.
    """

    def detect(
        self,
        previous_state: GameState | None,
        current_state: GameState,
    ) -> list[GameEvent]:
        """Return events for one state transition when rules are available."""
        if previous_state is not None and previous_state.target_id != current_state.target_id:
            return []
        return []
