"""Scenario lifecycle orchestrator."""

from __future__ import annotations

from typing import Any

from ..domain.game_event import GameEvent
from ..domain.scenario import Scenario


class ScenarioEngine:
    """Coordinate prompt creation, AI decisions, MCP calls, and verification."""

    def __init__(
        self,
        prompt_builder: Any,
        execution_policy: Any,
        ai_agent: Any,
        mcp_gateway: Any,
    ) -> None:
        self.prompt_builder = prompt_builder
        self.execution_policy = execution_policy
        self.ai_agent = ai_agent
        self.mcp_gateway = mcp_gateway

    def handle_event(self, scenario: Scenario, event: GameEvent) -> None:
        """Handle one event after concrete adapters are implemented."""
        raise NotImplementedError("Scenario execution is not implemented yet")
