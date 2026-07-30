"""Presenter interfaces for UI output."""

from abc import ABC, abstractmethod


class ILogPresenter(ABC):
    """Port for logging to UI."""
    
    @abstractmethod
    def info(self, message: str) -> None:
        """Log info message."""
        pass
    
    @abstractmethod
    def success(self, message: str) -> None:
        """Log success message."""
        pass
    
    @abstractmethod
    def error(self, message: str) -> None:
        """Log error message."""
        pass
    
    @abstractmethod
    def warning(self, message: str) -> None:
        """Log warning message."""
        pass
    
    @abstractmethod
    def step(self, index: int, total: int, name: str) -> None:
        """Log step progress."""
        pass


class IStatusPresenter(ABC):
    """Port for status updates."""
    
    @abstractmethod
    def set_phase(self, phase: str) -> None:
        """Set current phase (idle, processing, delay)."""
        pass
    
    @abstractmethod
    def cycle_started(self, cycle_number: int) -> None:
        """Notify cycle started."""
        pass
    
    @abstractmethod
    def action_started(self, index: int, name: str) -> None:
        """Notify action started."""
        pass
    
    @abstractmethod
    def action_finished(self, index: int, name: str, elapsed_ms: float) -> None:
        """Notify action finished."""
        pass
