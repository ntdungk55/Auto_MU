"""Execute tool use case - orchestrates tool execution."""

import time
from typing import Optional
from domain.entities.tool import Tool
from domain.entities.action import AutoAction
from domain.entities.execution_result import ActionResult, CycleResult
from domain.value_objects.action_type import ActionType
from application.interfaces.presenters import ILogPresenter, IStatusPresenter
from application.interfaces.stop_controller import IStopController
from .execute_action import ExecuteActionUseCase


class ExecuteToolUseCase:
    """Use case for executing a complete tool."""
    
    def __init__(
        self,
        execute_action: ExecuteActionUseCase,
        log_presenter: ILogPresenter,
        status_presenter: IStatusPresenter,
        stop_controller: IStopController,
    ):
        self._execute_action = execute_action
        self._log = log_presenter
        self._status = status_presenter
        self._stop = stop_controller
    
    def execute(self, tool: Tool, start_index: int = 0) -> None:
        """Execute tool from start_index."""
        cycle_no = 0
        current_index = start_index
        
        while not self._stop.should_stop():
            cycle_no += 1
            self._status.on_cycle_started(cycle_no)
            self._log.log_info(f"[VÒNG {cycle_no}] BẮT ĐẦU")
            
            # Pre-delay
            if not self._sleep(tool.loop_pre_delay):
                return
            
            # Execute actions
            result = self._execute_cycle(tool, current_index)
            
            if result.cancelled:
                return
            
            # Handle goto/restart
            if result.next_action_index is not None:
                current_index = result.next_action_index
                continue
            
            # Cycle completed
            current_index = 0
            
            # Post-delay
            if not self._sleep(tool.loop_post_delay):
                return
            
            # Check loop settings
            if not tool.loop_enabled:
                self._log.log_success("✓ ĐÃ HOÀN THÀNH")
                return
            
            if tool.loop_mode == "count" and cycle_no >= tool.loop_count:
                self._log.log_success(f"✓ ĐÃ LẶP ĐỦ {tool.loop_count} LẦN")
                return
    
    def _execute_cycle(self, tool: Tool, start_index: int) -> CycleResult:
        """Execute one cycle of actions."""
        for i in range(start_index, len(tool.actions)):
            if self._stop.should_stop():
                return CycleResult(cancelled=True)
            
            action = tool.actions[i]
            self._status.on_action_started(i, action.name)
            
            # Determine if should block input
            should_block = (
                tool.block_input_enabled
                and action.action_type in (
                    ActionType.KEYBOARD,
                    ActionType.MOUSE_CLICK,
                    ActionType.IMAGE_DETECT,
                )
            )
            
            # Execute action
            result = self._execute_action.execute(
                action=action,
                block_input=should_block,
                block_duration=tool.block_input_duration,
            )
            
            self._status.on_action_finished(i, action.name, result.execution_time_ms)
            
            if result.cancelled:
                return CycleResult(cancelled=True)
            
            # Handle result
            next_index = self._handle_result(tool, action, result, i)
            if next_index is not None:
                return CycleResult(next_action_index=next_index)
            
            # Delay after action
            if not self._sleep(action.delay):
                return CycleResult(cancelled=True)
        
        return CycleResult(completed=True)
    
    def _handle_result(
        self,
        tool: Tool,
        action: AutoAction,
        result: ActionResult,
        index: int,
    ) -> Optional[int]:
        """Handle action result. Returns next index if jump needed."""
        if result.success:
            self._log.log_success("✓ Thành công")
            # Goto on success
            passive_mode = str(getattr(action, "passive_mode", "") or "")
            if action.goto_step_enabled and not (
                action.action_type == ActionType.READ_PASSIVE and passive_mode == "event_tracking"
            ):
                self._log.log_info(f"🔄 Nhảy về Step {action.goto_step_index + 1}")
                return action.goto_step_index
        else:
            self._log.log_error("✗ Thất bại/Timeout")
            # Goto on timeout
            if action.timeout_goto_enabled:
                self._log.log_warning(f"Timeout → nhảy về Step {action.timeout_goto_step_index + 1}")
                return action.timeout_goto_step_index
            # Restart on timeout
            if tool.restart_on_timeout:
                self._log.log_warning("Timeout → chạy lại từ đầu")
                return 0
            # Stop on timeout (default)
            if tool.stop_on_timeout:
                self._stop.request_stop()
        
        return None
    
    def _sleep(self, seconds: float) -> bool:
        """Interruptible sleep. Returns False if interrupted."""
        if seconds <= 0:
            return True
        end = time.time() + seconds
        while time.time() < end:
            if self._stop.should_stop():
                return False
            remaining = end - time.time()
            time.sleep(min(0.05, max(0.0, remaining)))
        return True
