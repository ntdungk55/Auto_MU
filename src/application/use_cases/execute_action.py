"""Execute single action use case."""

import time
from domain.entities.action import AutoAction
from domain.entities.execution_result import ActionResult
from application.interfaces.gateways import IInputBlockerGateway
from application.interfaces.presenters import ILogPresenter
from application.interfaces.stop_controller import IStopController
from application.services.action_handlers.base import ActionHandlerRegistry


class ExecuteActionUseCase:
    """Use case for executing a single action."""
    
    def __init__(
        self,
        handler_registry: ActionHandlerRegistry,
        input_blocker: IInputBlockerGateway,
        log_presenter: ILogPresenter,
        stop_controller: IStopController,
    ):
        self._handler_registry = handler_registry
        self._input_blocker = input_blocker
        self._log_presenter = log_presenter
        self._stop_controller = stop_controller
    
    def execute(
        self,
        action: AutoAction,
        block_input: bool = False,
        block_duration: float = 3.0,
    ) -> ActionResult:
        """Execute action with optional input blocking."""
        start_time = time.perf_counter()
        did_block = False
        
        try:
            # Block input if enabled
            if block_input:
                did_block = self._input_blocker.block()
                if did_block:
                    self._log_presenter.log_info("🔒 Đã khóa input")
                    time.sleep(0.1)  # Stabilize
            
            # Get handler and execute
            handler = self._handler_registry.get_handler(action)
            result = handler.execute(action)
            
            # Calculate execution time
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            return result
            
        finally:
            # Always unblock
            if did_block:
                self._input_blocker.unblock()
                elapsed = time.perf_counter() - start_time
                self._log_presenter.log_info(f"🔓 Đã mở khóa input ({elapsed:.2f}s)")
