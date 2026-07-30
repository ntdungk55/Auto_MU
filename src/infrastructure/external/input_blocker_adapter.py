"""Adapter for input blocking via MouseController."""

from application.interfaces.gateways import IInputBlockerGateway


class InputBlockerAdapter(IInputBlockerGateway):
    """Adapter wrapping MouseController.block_input()."""
    
    def __init__(self, mouse_controller):
        """Initialize with existing MouseController instance."""
        self._controller = mouse_controller
    
    def block(self) -> bool:
        """Block user input."""
        if self._controller and hasattr(self._controller, 'block_input'):
            return self._controller.block_input(True)
        return False
    
    def unblock(self) -> None:
        """Unblock user input."""
        if self._controller and hasattr(self._controller, 'block_input'):
            self._controller.block_input(False)
