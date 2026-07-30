"""Stop controller implementation."""

from application.interfaces.stop_controller import IStopController


class StopController(IStopController):
    """Simple stop controller with flag-based control."""
    
    def __init__(self):
        self._should_stop = False
        self._cancel_cycle = False
    
    def should_stop(self) -> bool:
        """Check if execution should stop."""
        return self._should_stop
    
    def request_stop(self) -> None:
        """Request stop execution."""
        self._should_stop = True
    
    def should_cancel_cycle(self) -> bool:
        """Check if current cycle should be cancelled."""
        return self._cancel_cycle
    
    def request_cancel_cycle(self) -> None:
        """Request cancel current cycle."""
        self._cancel_cycle = True
    
    def reset(self) -> None:
        """Reset all flags."""
        self._should_stop = False
        self._cancel_cycle = False
    
    def reset_cancel_cycle(self) -> None:
        """Reset only cancel cycle flag."""
        self._cancel_cycle = False
