"""Status presenter using PyQt signals."""

from application.interfaces.presenters import IStatusPresenter


class SignalStatusPresenter(IStatusPresenter):
    """Presenter that emits status via PyQt signals."""
    
    def __init__(self, signals):
        """Initialize with signals object containing status signals."""
        self._signals = signals
    
    def on_cycle_started(self, cycle_number: int) -> None:
        """Notify cycle started."""
        if hasattr(self._signals, 'cycle_started'):
            self._signals.cycle_started.emit(cycle_number)
    
    def on_action_started(self, index: int, name: str) -> None:
        """Notify action started."""
        if hasattr(self._signals, 'action_started'):
            self._signals.action_started.emit(index, name)
    
    def on_action_finished(self, index: int, name: str, time_ms: float) -> None:
        """Notify action finished."""
        if hasattr(self._signals, 'action_finished'):
            self._signals.action_finished.emit(index, name, time_ms)
