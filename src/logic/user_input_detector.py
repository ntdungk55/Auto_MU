"""User Input Detector - Detect user mouse/keyboard input using global hooks."""

import threading
import ctypes
import win32gui
from typing import Optional, Callable

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    mouse = None
    keyboard = None

from PyQt6.QtCore import QObject, pyqtSignal


class UserInputDetector(QObject):
    """Detect user mouse/keyboard input using global hooks.
    
    Uses pynput for global hooks and checks dwExtraInfo to distinguish
    between tool-generated events and user events.
    """
    
    # Signal emitted when user input detected (type: "mouse" or "keyboard")
    user_input_detected = pyqtSignal(str)
    
    # Magic marker matching MouseController.TOOL_MARKER
    TOOL_MARKER = 0xAB10
    
    def __init__(self, target_hwnd: int = None, ui_log_func: Callable = None):
        """Initialize detector with target window handle.
        
        Args:
            target_hwnd: Target window handle to monitor
            ui_log_func: Optional logging function
        """
        super().__init__()
        self._target_hwnd = target_hwnd
        self._ui_log = ui_log_func or (lambda x: None)
        
        self._is_listening = False
        self._is_tool_acting = False
        self._mouse_listener = None
        self._keyboard_listener = None
        self._lock = threading.Lock()
    
    def set_target_window(self, hwnd: int):
        """Set target window handle."""
        self._target_hwnd = hwnd
    
    def set_tool_acting(self, is_acting: bool):
        """Set flag when tool is performing action.
        
        Args:
            is_acting: True when tool is sending input, False otherwise
        """
        with self._lock:
            self._is_tool_acting = is_acting
    
    def start_listening(self) -> bool:
        """Start global input hooks on separate thread.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not PYNPUT_AVAILABLE:
            self._ui_log("<b style='color:orange;'>[UserInput]</b> pynput not available, detection disabled")
            return False
        
        if self._is_listening:
            return True
        
        try:
            # Start mouse listener
            self._mouse_listener = mouse.Listener(
                on_click=self._on_mouse_click,
            )
            self._mouse_listener.start()
            
            # Start keyboard listener
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
            )
            self._keyboard_listener.start()
            
            self._is_listening = True
            self._ui_log("<b style='color:blue;'>[UserInput]</b> Started listening for user input")
            return True
            
        except Exception as e:
            self._ui_log(f"<b style='color:red;'>[UserInput]</b> Failed to start: {e}")
            self.stop_listening()
            return False
    
    def stop_listening(self):
        """Stop hooks and cleanup."""
        self._is_listening = False
        
        try:
            if self._mouse_listener:
                self._mouse_listener.stop()
                self._mouse_listener = None
        except Exception:
            pass
        
        try:
            if self._keyboard_listener:
                self._keyboard_listener.stop()
                self._keyboard_listener = None
        except Exception:
            pass
    
    def _is_in_target_window(self, x: int, y: int) -> bool:
        """Check if coordinates are within target window.
        
        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
            
        Returns:
            True if coordinates are within target window
        """
        if not self._target_hwnd:
            return False
        
        try:
            rect = win32gui.GetWindowRect(self._target_hwnd)
            return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]
        except Exception:
            return False
    
    def _is_tool_event(self) -> bool:
        """Check if current event is from tool (using flag).
        
        Note: dwExtraInfo check via pynput is not reliable on all systems,
        so we primarily use the _is_tool_acting flag.
        
        Returns:
            True if event is from tool
        """
        with self._lock:
            return self._is_tool_acting
    
    def _on_mouse_click(self, x: int, y: int, button, pressed: bool):
        """Handle mouse click event from hook.
        
        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
            button: Mouse button
            pressed: True if button pressed, False if released
        """
        if not self._is_listening:
            return
        
        # Only handle press events
        if not pressed:
            return
        
        # Check if this is a tool event
        if self._is_tool_event():
            return
        
        # Check if click is in target window
        if not self._is_in_target_window(x, y):
            return
        
        # Emit signal for user input
        try:
            self.user_input_detected.emit("mouse")
        except Exception:
            pass
    
    def _on_key_press(self, key):
        """Handle keyboard press event from hook.
        
        Args:
            key: Key that was pressed
        """
        if not self._is_listening:
            return
        
        # Check if this is a tool event
        if self._is_tool_event():
            return
        
        # Check if target window is focused
        if not self._is_target_window_focused():
            return
        
        # Emit signal for user input
        try:
            self.user_input_detected.emit("keyboard")
        except Exception:
            pass
    
    def _is_target_window_focused(self) -> bool:
        """Check if target window is currently focused.
        
        Returns:
            True if target window is focused
        """
        if not self._target_hwnd:
            return False
        
        try:
            foreground = ctypes.windll.user32.GetForegroundWindow()
            return foreground == self._target_hwnd
        except Exception:
            return False
    
    def __del__(self):
        """Cleanup on destruction."""
        self.stop_listening()
