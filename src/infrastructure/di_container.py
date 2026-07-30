"""Dependency Injection Container - wires all components."""

from application.services.action_handlers import (
    ActionHandlerRegistry,
    KeyboardActionHandler,
    MouseClickActionHandler,
    WaitActionHandler,
    ImageDetectActionHandler,
    ReadPassiveActionHandler,
    EventNotifyActionHandler,
)
from application.use_cases import ExecuteActionUseCase, ExecuteToolUseCase
from .external import SystemExecutorAdapter, InputBlockerAdapter, StopController
from .ui import SignalLogPresenter, SignalStatusPresenter


class DIContainer:
    """Simple DI container for wiring dependencies."""
    
    def __init__(self, executor, signals):
        """Initialize container with existing executor and signals."""
        self._executor = executor
        self._signals = signals
        self._instances = {}
    
    def get_stop_controller(self) -> StopController:
        """Get or create StopController."""
        if 'stop_controller' not in self._instances:
            self._instances['stop_controller'] = StopController()
        return self._instances['stop_controller']
    
    def get_executor_adapter(self) -> SystemExecutorAdapter:
        """Get or create SystemExecutorAdapter."""
        if 'executor_adapter' not in self._instances:
            self._instances['executor_adapter'] = SystemExecutorAdapter(self._executor)
        return self._instances['executor_adapter']
    
    def get_input_blocker(self) -> InputBlockerAdapter:
        """Get or create InputBlockerAdapter."""
        if 'input_blocker' not in self._instances:
            controller = getattr(self._executor, 'mouse_controller', None)
            self._instances['input_blocker'] = InputBlockerAdapter(controller)
        return self._instances['input_blocker']
    
    def get_log_presenter(self) -> SignalLogPresenter:
        """Get or create SignalLogPresenter."""
        if 'log_presenter' not in self._instances:
            self._instances['log_presenter'] = SignalLogPresenter(self._signals.log)
        return self._instances['log_presenter']
    
    def get_status_presenter(self) -> SignalStatusPresenter:
        """Get or create SignalStatusPresenter."""
        if 'status_presenter' not in self._instances:
            self._instances['status_presenter'] = SignalStatusPresenter(self._signals)
        return self._instances['status_presenter']
    
    def get_handler_registry(self) -> ActionHandlerRegistry:
        """Get or create ActionHandlerRegistry with all handlers."""
        if 'handler_registry' not in self._instances:
            registry = ActionHandlerRegistry()
            executor = self.get_executor_adapter()
            stop = self.get_stop_controller()
            
            # Register handlers
            registry.register(KeyboardActionHandler(executor))
            registry.register(MouseClickActionHandler(executor))
            registry.register(WaitActionHandler(stop))
            registry.register(ImageDetectActionHandler(executor))
            registry.register(ReadPassiveActionHandler(executor))
            registry.register(EventNotifyActionHandler())
            
            self._instances['handler_registry'] = registry
        return self._instances['handler_registry']
    
    def get_execute_action_use_case(self) -> ExecuteActionUseCase:
        """Get or create ExecuteActionUseCase."""
        if 'execute_action' not in self._instances:
            self._instances['execute_action'] = ExecuteActionUseCase(
                handler_registry=self.get_handler_registry(),
                input_blocker=self.get_input_blocker(),
                log_presenter=self.get_log_presenter(),
                stop_controller=self.get_stop_controller(),
            )
        return self._instances['execute_action']
    
    def get_execute_tool_use_case(self) -> ExecuteToolUseCase:
        """Get or create ExecuteToolUseCase."""
        if 'execute_tool' not in self._instances:
            self._instances['execute_tool'] = ExecuteToolUseCase(
                execute_action=self.get_execute_action_use_case(),
                log_presenter=self.get_log_presenter(),
                status_presenter=self.get_status_presenter(),
                stop_controller=self.get_stop_controller(),
            )
        return self._instances['execute_tool']
