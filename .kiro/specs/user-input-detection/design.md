# Design Document: User Input Detection

## Overview

Tính năng này cho phép hệ thống phát hiện khi người dùng thao tác chuột/bàn phím trong khi tool đang chạy, và phản ứng theo cấu hình (ignore/pause/stop). Sử dụng kết hợp:
1. **dwExtraInfo marker**: Đánh dấu input events từ tool với magic number
2. **Global hook**: Hook chuột/bàn phím để phát hiện user input
3. **Window boundary check**: Chỉ xử lý input trong target window

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MainWindow                              │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  Tool Settings  │  │  Running Table  │                   │
│  │  Dialog         │  │  (Status)       │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                             │
│           ▼                    ▼                             │
│  ┌─────────────────────────────────────────┐                │
│  │            ToolRunner                    │                │
│  │  - user_input_mode: str                  │                │
│  │  - pause_duration: int                   │                │
│  │  - is_paused_by_user: bool               │                │
│  └────────────────────┬────────────────────┘                │
│                       │                                      │
│                       ▼                                      │
│  ┌─────────────────────────────────────────┐                │
│  │        UserInputDetector                 │                │
│  │  - _hook_thread: Thread                  │                │
│  │  - _is_tool_acting: bool                 │                │
│  │  - _target_hwnd: int                     │                │
│  │  + start_listening()                     │                │
│  │  + stop_listening()                      │                │
│  │  + set_tool_acting(bool)                 │                │
│  │  + signal: user_input_detected           │                │
│  └────────────────────┬────────────────────┘                │
│                       │                                      │
│                       ▼                                      │
│  ┌─────────────────────────────────────────┐                │
│  │        MouseController                   │                │
│  │  - TOOL_MARKER = 0xAUT0                  │                │
│  │  + click_with_marker()                   │                │
│  └─────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. UserInputDetector (src/logic/user_input_detector.py)

```python
class UserInputDetector(QObject):
    """Detect user mouse/keyboard input using global hooks."""
    
    # Signal emitted when user input detected
    user_input_detected = pyqtSignal(str)  # "mouse" or "keyboard"
    
    TOOL_MARKER = 0xAUT0  # Magic number to mark tool events
    
    def __init__(self, target_hwnd: int):
        """Initialize detector with target window handle."""
        
    def start_listening(self):
        """Start global input hooks on separate thread."""
        
    def stop_listening(self):
        """Stop hooks and cleanup."""
        
    def set_tool_acting(self, is_acting: bool):
        """Set flag when tool is performing action."""
        
    def _is_in_target_window(self, x: int, y: int) -> bool:
        """Check if coordinates are within target window."""
        
    def _on_mouse_event(self, event) -> bool:
        """Handle mouse event from hook."""
        
    def _on_keyboard_event(self, event) -> bool:
        """Handle keyboard event from hook."""
```

### 2. MouseController Updates (src/logic/system_executor/mouse_controller.py)

```python
class MouseController:
    TOOL_MARKER = 0xAUT0  # Same marker as UserInputDetector
    
    def _send_input_with_marker(self, inputs: list):
        """Send input events with dwExtraInfo marker."""
        for inp in inputs:
            inp.mi.dwExtraInfo = self.TOOL_MARKER
        # ... send inputs
```

### 3. ToolRunner Updates (main.py)

```python
class ToolRunner:
    def __init__(self, ...):
        # New fields
        self.user_input_mode = "ignore"  # "ignore" | "pause" | "stop"
        self.pause_duration = 5  # seconds
        self.is_paused_by_user = False
        self.user_input_detector = None
        
    def _on_user_input_detected(self, input_type: str):
        """Handle user input detection."""
        if self.user_input_mode == "ignore":
            return
        elif self.user_input_mode == "pause":
            self._pause_for_duration()
        elif self.user_input_mode == "stop":
            self.stop()
```

### 4. Tool Settings Dialog Updates

Thêm section "User Input Mode" vào ToolSettingsDialog:
- Radio buttons: Ignore / Pause / Stop
- SpinBox cho pause duration (khi chọn Pause)

## Data Models

### Tool JSON Schema Update

```json
{
  "name": "MyTool",
  "actions": [...],
  "user_input_mode": "pause",
  "pause_duration": 5
}
```

### ToolRunner Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| user_input_mode | str | "ignore" | "ignore", "pause", "stop" |
| pause_duration | int | 5 | Seconds to pause (1-300) |

## Implementation Details

### dwExtraInfo Marker

Windows `SendInput()` API cho phép set `dwExtraInfo` field trong `MOUSEINPUT` và `KEYBDINPUT` structures. Tool sẽ:
1. Set `dwExtraInfo = 0xAUT0` khi gửi input
2. Hook kiểm tra `dwExtraInfo` của incoming events
3. Nếu `dwExtraInfo == 0xAUT0` → ignore (từ tool)
4. Nếu `dwExtraInfo != 0xAUT0` → user input

### Global Hook Implementation

Sử dụng `pynput` library:
```python
from pynput import mouse, keyboard

# Mouse hook
mouse_listener = mouse.Listener(
    on_click=self._on_mouse_click,
    on_move=self._on_mouse_move
)

# Keyboard hook  
keyboard_listener = keyboard.Listener(
    on_press=self._on_key_press
)
```

### Window Boundary Check

```python
def _is_in_target_window(self, x: int, y: int) -> bool:
    import win32gui
    rect = win32gui.GetWindowRect(self._target_hwnd)
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]
```

## Error Handling

1. **Hook fails to start**: Log warning, continue without detection
2. **Target window closed**: Stop listening, log message
3. **Exception in hook callback**: Catch and log, don't crash
4. **App closes while hook active**: Ensure cleanup in destructor

## Testing Strategy

### Unit Tests
- Test dwExtraInfo marker is set correctly
- Test window boundary check logic
- Test mode switching (ignore/pause/stop)

### Manual Tests
1. Run tool, click mouse in game window → verify pause/stop
2. Run tool, click mouse outside game window → verify no effect
3. Run tool, press keyboard in game window → verify pause/stop
4. Verify tool's own clicks don't trigger detection
5. Verify pause duration works correctly
6. Verify settings persist after restart

## Dependencies

- `pynput`: Global keyboard/mouse hooks
- `pywin32`: Windows API for window rect, SendInput

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Antivirus blocks hooks | Document as known issue, provide whitelist instructions |
| Performance impact | Run hooks on separate thread, minimal processing |
| Race conditions | Use thread-safe flags, proper locking |
| Hook not working on some systems | Graceful fallback, log warnings |
