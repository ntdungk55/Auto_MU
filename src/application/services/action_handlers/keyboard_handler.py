"""Keyboard action handler."""

from domain.entities.action import AutoAction
from domain.entities.execution_result import ActionResult
from domain.value_objects.action_type import ActionType
from application.interfaces.gateways import IActionExecutorGateway
from .base import IActionHandler


class KeyboardActionHandler(IActionHandler):
    """Handler for KEYBOARD actions."""
    
    def __init__(self, executor: IActionExecutorGateway):
        self._executor = executor
    
    def can_handle(self, action: AutoAction) -> bool:
        """Check if this handler can handle the action."""
        return action.action_type == ActionType.KEYBOARD
    
    def execute(self, action: AutoAction) -> ActionResult:
        """Execute keyboard action."""
        success = self._executor.execute_keyboard(
            key=action.key,
            modifiers=action.modifiers
        )
        return ActionResult(
            success=success,
            action_name=action.name,
            action_type=action.action_type
        )
