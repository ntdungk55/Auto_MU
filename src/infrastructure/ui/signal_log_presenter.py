"""Log presenter using PyQt signals."""

from application.interfaces.presenters import ILogPresenter


class SignalLogPresenter(ILogPresenter):
    """Presenter that emits logs via PyQt signal."""
    
    def __init__(self, log_signal):
        """Initialize with PyQt signal for logging."""
        self._signal = log_signal
    
    def log_info(self, message: str) -> None:
        """Log info message."""
        self._signal.emit(f"<b>{message}</b>")
    
    def log_success(self, message: str) -> None:
        """Log success message."""
        self._signal.emit(f"<b style='color:green;'>{message}</b>")
    
    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self._signal.emit(f"<b style='color:orange;'>{message}</b>")
    
    def log_error(self, message: str) -> None:
        """Log error message."""
        self._signal.emit(f"<b style='color:red;'>{message}</b>")
