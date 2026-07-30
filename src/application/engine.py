"""Clean Architecture Engine - wraps existing AutoBotEngine logic."""

import threading
import time
from typing import Optional

from domain.entities.tool import Tool as DomainTool
from domain.entities.action import AutoAction as DomainAction
from domain.value_objects.action_type import ActionType as DomainActionType
from application.use_cases import ExecuteToolUseCase
from infrastructure.di_container import DIContainer
from infrastructure.external import StopController


class CleanArchitectureEngine:
    """Engine using Clean Architecture - delegates to Use Cases."""
    
    def __init__(self, signals, executor, tool_manager=None):
        """Initialize with signals and executor."""
        self.signals = signals
        self.executor = executor
        self.tool_manager = tool_manager
        
        # State
        self.is_running = False
        self.should_stop_completely = False
        self.current_tool = None
        self.current_action_index = 0
        self.loop_cycles_done = 0
        
        # DI Container
        self._container: Optional[DIContainer] = None
        self._stop_controller: Optional[StopController] = None
    
    def _init_container(self) -> None:
        """Initialize DI container lazily."""
        if self._container is None:
            self._container = DIContainer(self.executor, self.signals)
            self._stop_controller = self._container.get_stop_controller()
    
    def start(self, tool, resume: bool = False, target_window_hwnd=None) -> None:
        """Start tool execution."""
        self._init_container()
        
        if not resume:
            self.should_stop_completely = False
            self.current_tool = tool
            self.current_action_index = 0
            self.loop_cycles_done = 0
            self.signals.log.emit(f"<b>BẮT ĐẦU:</b> Tool: {tool.name}")
        
        if not self.is_running:
            self.is_running = True
            self._stop_controller.reset()
            threading.Thread(target=self._run, daemon=True).start()
    
    def stop(self) -> None:
        """Pause execution."""
        self.is_running = False
        if self._stop_controller:
            self._stop_controller.request_stop()
        self.signals.log.emit("<b style='color:orange;'>ĐÃ DỪNG</b>")
    
    def stop_completely(self) -> None:
        """Stop and reset."""
        self.is_running = False
        self.should_stop_completely = True
        self.current_tool = None
        self.current_action_index = 0
        self.loop_cycles_done = 0
        if self._stop_controller:
            self._stop_controller.request_stop()
        self.signals.log.emit("<b style='color:red;'>ĐÃ DỪNG HOÀN TOÀN</b>")
    
    def request_cancel_cycle(self) -> None:
        """Cancel current cycle."""
        if self._stop_controller:
            self._stop_controller.request_cancel_cycle()
    
    def _run(self) -> None:
        """Run tool in background thread."""
        if not self.current_tool:
            return
        
        try:
            # Convert legacy Tool to domain Tool
            domain_tool = self._to_domain_tool(self.current_tool)
            
            # Get use case and execute
            use_case = self._container.get_execute_tool_use_case()
            use_case.execute(domain_tool, self.current_action_index)
            
        except Exception as e:
            self.signals.log.emit(f"<b style='color:red;'>Lỗi: {e}</b>")
        finally:
            self.is_running = False
    
    def _to_domain_tool(self, legacy_tool) -> DomainTool:
        """Convert legacy Tool to domain Tool."""
        actions = [self._to_domain_action(a) for a in legacy_tool.actions]
        
        return DomainTool(
            name=legacy_tool.name,
            actions=actions,
            loop_enabled=getattr(legacy_tool, 'loop_enabled', False),
            loop_mode=getattr(legacy_tool, 'loop_mode', 'forever'),
            loop_count=getattr(legacy_tool, 'loop_count', 1),
            loop_pre_delay_100ms=getattr(legacy_tool, 'loop_pre_delay_100ms', 0),
            loop_post_delay_100ms=getattr(legacy_tool, 'loop_post_delay_100ms', 0),
            stop_on_timeout=getattr(legacy_tool, 'stop_on_timeout', True),
            restart_on_timeout=getattr(legacy_tool, 'restart_on_timeout', False),
            block_input_enabled=getattr(legacy_tool, 'block_input_enabled', False),
            block_input_duration=getattr(legacy_tool, 'block_input_duration', 3.0),
        )
    
    def _to_domain_action(self, legacy_action) -> DomainAction:
        """Convert legacy AutoAction to domain AutoAction."""
        # Map action type
        type_map = {
            'KEYBOARD': DomainActionType.KEYBOARD,
            'MOUSE_CLICK': DomainActionType.MOUSE_CLICK,
            'IMAGE_DETECT': DomainActionType.IMAGE_DETECT,
            'WAIT': DomainActionType.WAIT,
            'READ_PASSIVE': DomainActionType.READ_PASSIVE,
            'EVENT_NOTIFY': DomainActionType.EVENT_NOTIFY,
        }
        
        action_type = type_map.get(
            legacy_action.action_type.name,
            DomainActionType.KEYBOARD
        )
        
        return DomainAction(
            name=legacy_action.name,
            action_type=action_type,
            timeout=getattr(legacy_action, 'timeout', 30.0),
            delay=getattr(legacy_action, 'delay', 0.0),
            check_interval=getattr(legacy_action, 'check_interval', 0.5),
            goto_step_enabled=getattr(legacy_action, 'goto_step_enabled', False),
            goto_step_index=getattr(legacy_action, 'goto_step_index', 0),
            timeout_goto_enabled=getattr(legacy_action, 'timeout_goto_enabled', False),
            timeout_goto_step_index=getattr(legacy_action, 'timeout_goto_step_index', 0),
            key=getattr(legacy_action, 'key', ''),
            modifiers=getattr(legacy_action, 'modifiers', []),
            image_path=getattr(legacy_action, 'image_path', ''),
            threshold=getattr(legacy_action, 'threshold', 0.8),
            click_by_coordinate=getattr(legacy_action, 'click_by_coordinate', False),
            click_x=getattr(legacy_action, 'click_x', 0),
            click_y=getattr(legacy_action, 'click_y', 0),
            fixed_roi_enabled=getattr(legacy_action, 'fixed_roi_enabled', False),
            fixed_roi=getattr(legacy_action, 'fixed_roi', None),
            gemini_enabled=getattr(legacy_action, 'gemini_enabled', False),
            gemini_prompt=getattr(legacy_action, 'gemini_prompt', ''),
            send_telegram=getattr(legacy_action, 'send_telegram', False),
        )
