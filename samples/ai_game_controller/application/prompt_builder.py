"""AI prompt composition."""

from __future__ import annotations

import json

from ..domain.game_event import GameEvent
from ..domain.scenario import Scenario


class PromptBuilder:
    """Build one AI input from system rules, scenario, event, and game state."""

    def build(self, system_prompt: str, scenario: Scenario, event: GameEvent) -> str:
        """Build a provider-neutral event prompt without invoking an AI client."""
        event_payload = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "target_id": event.target_id,
            "created_at": event.created_at.isoformat(),
            "changed_fields": list(event.changed_fields),
            "current_state": event.current_state.main_info,
            "previous_state": event.previous_state.main_info if event.previous_state else None,
        }
        scenario_payload = {
            "scenario_id": scenario.scenario_id,
            "name": scenario.name,
            "instruction": scenario.instruction,
            "allowed_tools": list(scenario.allowed_tools),
            "max_tool_calls_per_event": scenario.max_tool_calls_per_event,
        }
        return "\n\n".join(
            (
                system_prompt.strip(),
                "Active scenario:\n" + json.dumps(scenario_payload, ensure_ascii=False, indent=2),
                "Game event:\n" + json.dumps(event_payload, ensure_ascii=False, indent=2),
            )
        )
