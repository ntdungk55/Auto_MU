"""Background game-state reader adapter."""

from __future__ import annotations

from ..domain.game_state import GameState


class GameStateReader:
    """Capture configured game windows and publish normalized OCR snapshots."""

    def read_all(self) -> list[GameState]:
        """Read every valid target after the OCR pipeline is implemented."""
        raise NotImplementedError("Game-state capture is not implemented yet")
