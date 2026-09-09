"""AI prompt composition."""

from __future__ import annotations

from ..domain.game_event import GameEvent
from ..domain.scenario import Scenario


class PromptBuilder:
    """Build one AI input from system rules, scenario, event, and game state."""

    def build(self, system_prompt: str, scenario: Scenario, event: GameEvent) -> str:
        """Build the event prompt after its final schema is approved."""
        raise NotImplementedError("Prompt composition is not implemented yet")
