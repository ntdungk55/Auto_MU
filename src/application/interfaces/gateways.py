"""Gateway interfaces (Ports) for external services."""

from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.action import AutoAction


class IActionExecutorGateway(ABC):
    """Port for action execution."""
    
    @abstractmethod
    def execute_keyboard(self, key: str, modifiers: list[str]) -> bool:
        """Execute keyboard action."""
        pass
    
    @abstractmethod
    def execute_mouse_click(self, x: int, y: int) -> bool:
        """Execute mouse click at coordinates."""
        pass
    
    @abstractmethod
    def find_image(
        self, 
        template_path: str, 
        threshold: float,
        roi: Optional[tuple[int, int, int, int]] = None
    ) -> Optional[tuple[int, int]]:
        """Find image on screen. Returns center (x, y) if found."""
        pass
    
    @abstractmethod
    def execute(self, action: AutoAction) -> bool:
        """Execute action (legacy interface)."""
        pass
    
    @abstractmethod
    def execute_with_timeout(
        self, 
        action: AutoAction, 
        timeout: float
    ) -> Optional[bool]:
        """Execute action with timeout. Returns None if cancelled."""
        pass


class IInputBlockerGateway(ABC):
    """Port for input blocking."""
    
    @abstractmethod
    def block(self) -> bool:
        """Block user input. Returns True if successful."""
        pass
    
    @abstractmethod
    def unblock(self) -> None:
        """Unblock user input."""
        pass


class IWindowGateway(ABC):
    """Port for window operations."""
    
    @abstractmethod
    def set_foreground(self, hwnd: int) -> bool:
        """Set window to foreground."""
        pass
    
    @abstractmethod
    def capture_screenshot(self, hwnd: int) -> Optional[bytes]:
        """Capture window screenshot."""
        pass
