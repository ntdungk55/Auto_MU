"""Execution result value objects."""

from dataclasses import dataclass, field
from typing import Optional
from ..value_objects.action_type import ActionType


@dataclass
class ActionResult:
    """Result of action execution."""
    success: bool
    action_name: str = ""
    action_type: Optional[ActionType] = None
    execution_time_ms: float = 0.0
    timed_out: bool = False
    cancelled: bool = False
    error_message: str = ""


@dataclass
class CycleResult:
    """Result of cycle execution."""
    completed: bool = False
    cancelled: bool = False
    next_action_index: Optional[int] = None
    elapsed_ms: float = 0.0
