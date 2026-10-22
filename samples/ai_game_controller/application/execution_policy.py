"""AI tool-call execution policy."""

from __future__ import annotations

from ..domain.scenario import Scenario


class ExecutionPolicy:
    """Validate tool permissions, target ownership, limits, and cancellation."""

    def validate_tool_call(
        self,
        scenario: Scenario,
        tool_name: str,
        tool_call_count: int,
    ) -> None:
        """Reject a disallowed tool call after policy errors are defined."""
        raise NotImplementedError("Tool-call policy is not implemented yet")
