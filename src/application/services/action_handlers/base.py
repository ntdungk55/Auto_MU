"""Base action handler interface and registry."""

from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.action import AutoAction
from domain.entities.execution_result import ActionResult


class IActionHandler(ABC):
    """Strategy interface for action handling."""
    
    @abstractmethod
    def can_handle(self, action: AutoAction) -> bool:
        """Check if this handler can handle the action."""
        pass
    
    @abstractmethod
    def execute(self, action: AutoAction) -> ActionResult:
        """Execute the action and return result."""
        pass


class ActionHandlerRegistry:
    """Registry for action handlers - Single Source of Truth."""
    
    def __init__(self):
        self._handlers: list[IActionHandler] = []
    
    def register(self, handler: IActionHandler) -> None:
        """Register a handler."""
        self._handlers.append(handler)
    
    def get_handler(self, action: AutoAction) -> IActionHandler:
        """Get appropriate handler for action."""
        for handler in self._handlers:
            if handler.can_handle(action):
                return handler
        raise ValueError(f"No handler for action type: {action.action_type}")
