"""Scenario domain model."""

from __future__ import annotations

from dataclasses import dataclass, field


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
