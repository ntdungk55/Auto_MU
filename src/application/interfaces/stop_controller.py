"""Stop controller interface."""

from abc import ABC, abstractmethod


class IStopController(ABC):
    """Port for stop control."""
    
    @abstractmethod
    def should_stop(self) -> bool:
        """Check if execution should stop completely."""
        pass
    
    @abstractmethod
    def should_cancel_cycle(self) -> bool:
        """Check if current cycle should be cancelled."""
        pass
    
    @abstractmethod
    def clear_cancel_flag(self) -> None:
        """Clear the cancel cycle flag."""
        pass
