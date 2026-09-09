"""Sample process lifecycle controller."""

from __future__ import annotations

from typing import Any


class ProcessController:
    """Own Start, Stop, Restart, and Emergency Stop transitions."""

    def __init__(self, game_state_reader: Any, scenario_engine: Any) -> None:
        self.game_state_reader = game_state_reader
        self.scenario_engine = scenario_engine
        self.is_running = False

    def start(self) -> None:
        """Start the runtime after worker lifecycle is implemented."""
        raise NotImplementedError("Process start is not implemented yet")

    def stop(self) -> None:
        """Stop the runtime after cancellation handling is implemented."""
        raise NotImplementedError("Process stop is not implemented yet")
