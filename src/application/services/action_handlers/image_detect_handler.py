"""Image detect action handler."""

from domain.entities.action import AutoAction
from domain.entities.execution_result import ActionResult
from domain.value_objects.action_type import ActionType
from application.interfaces.gateways import IActionExecutorGateway
from .base import IActionHandler


class ImageDetectActionHandler(IActionHandler):
    """Handler for IMAGE_DETECT actions."""
    
    def __init__(self, executor: IActionExecutorGateway):
        self._executor = executor
    
    def can_handle(self, action: AutoAction) -> bool:
        """Check if this handler can handle the action."""
        return action.action_type == ActionType.IMAGE_DETECT
    
    def execute(self, action: AutoAction) -> ActionResult:
        """Execute image detect action with timeout."""
        success = self._executor.execute_with_timeout(
            action=action,
            timeout=action.timeout
        )
        
        # None means cancelled
        if success is None:
            return ActionResult(
                success=False,
                action_name=action.name,
                action_type=action.action_type,
                cancelled=True
            )
        
        return ActionResult(
            success=success,
            action_name=action.name,
            action_type=action.action_type,
            timed_out=not success
        )
