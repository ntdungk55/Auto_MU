"""Adapter wrapping existing SystemExecutor."""

from typing import Optional
from domain.entities.action import AutoAction
from application.interfaces.gateways import IActionExecutorGateway


class SystemExecutorAdapter(IActionExecutorGateway):
    """Adapter for existing SystemExecutor - delegates all calls."""
    
    def __init__(self, executor):
        """Initialize with existing SystemExecutor instance."""
        self._executor = executor
    
    def execute_keyboard(self, key: str, modifiers: list[str]) -> bool:
        """Execute keyboard action via existing executor."""
        # Create minimal action for keyboard
        from src.logic.action_type import AutoAction as LegacyAction, ActionType
        action = LegacyAction(
            name="keyboard",
            action_type=ActionType.KEYBOARD,
            key=key,
            modifiers=modifiers,
        )
        return self._executor.execute(action)
    
    def execute_mouse_click(self, x: int, y: int) -> bool:
        """Execute mouse click via existing executor."""
        return self._executor.mouse_controller.click(x, y)
    
    def find_image(
        self,
        template_path: str,
        threshold: float,
        roi: Optional[tuple[int, int, int, int]] = None,
    ) -> Optional[tuple[int, int]]:
        """Find image via existing executor."""
        return self._executor.find_image(template_path, threshold, roi)
    
    def execute(self, action: AutoAction) -> bool:
        """Execute action via existing executor (legacy)."""
        # Convert domain action to legacy action
        legacy_action = self._to_legacy_action(action)
        return self._executor.execute(legacy_action)
    
    def execute_with_timeout(
        self,
        action: AutoAction,
        timeout: float,
    ) -> Optional[bool]:
        """Execute with timeout via existing executor."""
        legacy_action = self._to_legacy_action(action)
        return self._executor.execute_with_timeout(legacy_action, timeout)
    
    def _to_legacy_action(self, action: AutoAction):
        """Convert domain AutoAction to legacy AutoAction."""
        from src.logic.action_type import AutoAction as LegacyAction, ActionType
        
        # Map action type
        action_type_map = {
            'KEYBOARD': ActionType.KEYBOARD,
            'MOUSE_CLICK': ActionType.MOUSE_CLICK,
            'IMAGE_DETECT': ActionType.IMAGE_DETECT,
            'WAIT': ActionType.WAIT,
            'READ_PASSIVE': ActionType.READ_PASSIVE,
            'EVENT_NOTIFY': ActionType.EVENT_NOTIFY,
        }
        
        legacy_type = action_type_map.get(action.action_type.name, ActionType.KEYBOARD)
        
        return LegacyAction(
            name=action.name,
            action_type=legacy_type,
            timeout=action.timeout,
            delay=action.delay,
            check_interval=action.check_interval,
            key=action.key,
            modifiers=action.modifiers,
            image_path=action.image_path,
            threshold=action.threshold,
            click_by_coordinate=action.click_by_coordinate,
            click_x=action.click_x,
            click_y=action.click_y,
            fixed_roi_enabled=action.fixed_roi_enabled,
            fixed_roi=action.fixed_roi,
            gemini_enabled=action.gemini_enabled,
            gemini_prompt=action.gemini_prompt,
            event_notify_times=getattr(action, "event_notify_times", []) or [],
            event_prepare_start_s=int(getattr(action, "event_prepare_start_s", 300) or 300),
            event_prepare_end_s=int(getattr(action, "event_prepare_end_s", 60) or 60),
        )
