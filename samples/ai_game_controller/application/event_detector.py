"""Game-state event detection."""

from __future__ import annotations

from uuid import uuid4

from ..domain.game_event import GameEvent
from ..domain.game_state import GameState


class EventDetector:
    """Convert meaningful state transitions into game events.

    The first supported transition is a confirmed change of the OCR map name.
    """

    def detect(
        self,
        previous_state: GameState | None,
        current_state: GameState,
    ) -> list[GameEvent]:
        """Return a ``map.changed`` event when a non-empty map name changes."""
        if previous_state is not None and previous_state.target_id != current_state.target_id:
            return []
        if previous_state is None:
            return []

        previous_map = self._map_name(previous_state)
        current_map = self._map_name(current_state)
        if not previous_map or not current_map or previous_map.casefold() == current_map.casefold():
            return []

        return [
            GameEvent(
                event_id=f"map.changed:{current_state.target_id}:{uuid4().hex}",
                event_type="map.changed",
                target_id=current_state.target_id,
                current_state=current_state,
                previous_state=previous_state,
                created_at=current_state.captured_at,
                changed_fields=("map",),
            )
        ]

    @staticmethod
    def _map_name(state: GameState) -> str:
        """Read and normalize the map value produced by the teaching JSON OCR."""
        raw_map = state.main_info.get("map")
        if isinstance(raw_map, dict):
            raw_map = raw_map.get("text", "")
        return " ".join(str(raw_map or "").split())
