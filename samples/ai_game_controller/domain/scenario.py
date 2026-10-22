"""Scenario domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Scenario:
    """User instruction and execution limits for one game target."""

    scenario_id: str
    name: str
    instruction: str
    target_id: str
    enabled_events: tuple[str, ...] = field(default_factory=tuple)
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)
    event_cooldown_ms: int = 3000
    max_tool_calls_per_event: int = 20

    def to_dict(self) -> dict[str, Any]:
        """Serialize this scenario for JSON persistence."""
        return {
            "id": self.scenario_id,
            "name": self.name,
            "instruction": self.instruction,
            "targetId": self.target_id,
            "enabledEvents": list(self.enabled_events),
            "allowedTools": list(self.allowed_tools),
            "eventCooldownMs": self.event_cooldown_ms,
            "maxToolCallsPerEvent": self.max_tool_calls_per_event,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Scenario":
        """Build a scenario from the persisted JSON schema."""
        return cls(
            scenario_id=str(payload["id"]),
            name=str(payload["name"]),
            instruction=str(payload["instruction"]),
            target_id=str(payload["targetId"]),
            enabled_events=tuple(str(item) for item in payload.get("enabledEvents", [])),
            allowed_tools=tuple(str(item) for item in payload.get("allowedTools", [])),
            event_cooldown_ms=int(payload.get("eventCooldownMs", 3000)),
            max_tool_calls_per_event=int(payload.get("maxToolCallsPerEvent", 20)),
        )
