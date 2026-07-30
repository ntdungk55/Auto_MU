"""Wait action handler."""

import time
from domain.entities.action import AutoAction
from domain.entities.execution_result import ActionResult
from domain.value_objects.action_type import ActionType
from application.interfaces.stop_controller import IStopController
from .base import IActionHandler


class WaitActionHandler(IActionHandler):
    """Handler for WAIT actions."""
    
    def __init__(self, stop_controller: IStopController):
        self._stop_controller = stop_controller
    
    def can_handle(self, action: AutoAction) -> bool:
        """Check if this handler can handle the action."""
        return action.action_type == ActionType.WAIT
    
    def execute(self, action: AutoAction) -> ActionResult:
        """Execute wait action - sleep for timeout duration."""
        wait_time = action.timeout
        
        # Interruptible sleep
        end_time = time.time() + wait_time
        while time.time() < end_time:
            if self._stop_controller.should_stop():
                return ActionResult(
                    success=False,
                    action_name=action.name,
                    action_type=action.action_type,
                    cancelled=True
                )
            remaining = end_time - time.time()
            time.sleep(min(0.05, max(0.0, remaining)))
        
        return ActionResult(
            success=True,
            action_name=action.name,
            action_type=action.action_type
        )
