"""Game event domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .game_state import GameState


@dataclass(frozen=True, slots=True)
class GameEvent:
    """State transition that may trigger one AI scenario turn."""

    event_id: str
    event_type: str
    target_id: str
    current_state: GameState
    created_at: datetime
    previous_state: GameState | None = None
    changed_fields: tuple[str, ...] = field(default_factory=tuple)
