---
inclusion: auto
---

# Project Structure & Coding Standards

## Directory Organization

```
project/
├── main.py                          # Entry point only
├── requirements.txt                 # Dependencies
├── docs/                            # Documentation
│   ├── CURRENT_STATUS.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── ...
├── tests/                           # Test files
│   ├── test_action_data.py
│   ├── test_fixed_roi.py
│   └── __init__.py
├── src/
│   ├── __init__.py
│   ├── logic/                       # Pure business logic (no UI)
│   │   ├── __init__.py
│   │   ├── action_type.py           # Data models (AutoAction, ActionType)
│   │   ├── dpapi.py                 # Windows DPAPI encryption
│   │   ├── tool_manager.py          # Tool serialization/deserialization
│   │   ├── window_detector.py       # Window detection
│   │   ├── system_executor.py       # Wrapper for backward compatibility
│   │   ├── system_executor/         # Modular components (refactored)
│   │   │   ├── __init__.py
│   │   │   ├── system_executor.py   # Main orchestrator (~400 lines)
│   │   │   ├── ocr_engine.py        # OCR engines (WinRT, Tesseract)
│   │   │   ├── ocr_preprocessor.py  # Image preprocessing (builder pattern)
│   │   │   ├── window_capture.py    # Screenshot capture
│   │   │   ├── mouse_controller.py  # Mouse/keyboard input
│   │   │   ├── gemini_processor.py  # Gemini AI integration
│   │   │   └── telegram_notifier.py # Telegram notifications
│   │   └── notifications/           # Notification handlers
│   │       ├── __init__.py
│   │       ├── telegram.py
│   │       └── config_dialog.py
│   └── ui/                          # PyQt UI components (no business logic)
│       ├── __init__.py
│       ├── action_config_dialog.py
│       ├── gemini_chat_widget.py
│       ├── image_capture_dialog.py
│       ├── image_preprocessing_widget.py
│       ├── tool_editor_window.py
│       ├── tool_settings_dialog.py
│       └── ...
└── .kiro/
    ├── specs/                       # Feature specifications
    │   ├── gemini-integration-fix/
    │   │   ├── requirements.md
    │   │   ├── design.md
    │   │   └── tasks.md
    │   └── ...
    └── steering/                    # Project guidelines
        ├── project-structure.md     # This file
        └── ...
```

## Key Principles

### 1. Separation of Concerns
- **`src/logic/`** - Pure business logic, no UI dependencies
- **`src/ui/`** - PyQt UI components only, minimal logic
- **`tests/`** - Test files separate from source
- **`docs/`** - Documentation separate from code

### 2. Modular Architecture
- Each component has **single responsibility**
- Components in `system_executor/` are ~300-400 lines each
- Use **builder pattern** for complex object construction
- Use **factory pattern** for object creation

### 3. File Naming Conventions
- **snake_case** for file names: `ocr_engine.py`, `mouse_controller.py`
- **PascalCase** for class names: `SystemExecutor`, `OCREngine`
- **UPPER_CASE** for constants: `MOUSEEVENTF_LEFTDOWN`

### 4. Import Strategy
- **Relative imports** within packages: `from .ocr_engine import OCREngine`
- **Absolute imports** from parent: `from action_type import AutoAction`
- **Backward compatibility wrapper** at package level: `src/logic/system_executor.py`

### 5. Code Organization Within Files

#### Logic Files (src/logic/)
```python
"""Module docstring."""

# Standard library imports
import os
import sys

# Third-party imports
import cv2
import numpy as np

# Local imports
from .submodule import Class

# Constants
CONSTANT_NAME = value

# Helper functions (if any)
def helper_function():
    pass

# Main class
class MainClass:
    def __init__(self):
        pass
    
    def public_method(self):
        pass
    
    def _private_method(self):
        pass
```

#### UI Files (src/ui/)
```python
"""UI component docstring."""

from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import pyqtSignal

# Import logic from src/logic
from logic.action_type import AutoAction

class UIComponent(QDialog):
    # Signals
    data_changed = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        pass
    
    def _on_button_clicked(self):
        """Handle button click."""
        pass
```

## Component Responsibilities

### system_executor/ Package
- **system_executor.py** - Main orchestrator, action dispatcher
- **ocr_engine.py** - OCR abstraction (WinRT, Tesseract)
- **ocr_preprocessor.py** - Image preprocessing (upscale, contrast, sharpen, denoise)
- **window_capture.py** - Screenshot capture using Win32 API
- **mouse_controller.py** - Mouse/keyboard input handling
- **gemini_processor.py** - Gemini API integration
- **telegram_notifier.py** - Telegram notification sending

### action_type.py
- **AutoAction** - Data model for automation actions
- **ActionType** - Enum for action types (KEYBOARD, MOUSE_CLICK, IMAGE_DETECT, READ_PASSIVE)

### tool_manager.py
- Serialization/deserialization of tools to/from JSON
- Handles Fixed ROI, Gemini settings, OCR preprocessing config

### window_detector.py
- Window detection and management
- Window handle resolution

## Coding Standards

### Python Version
- Python 3.10+ (type hints, match statements)
- Use type hints for all function signatures

### Code Style
- Follow PEP 8
- Max line length: 120 characters
- Use docstrings for all public methods
- Use comments for complex logic

### Error Handling
- Use try/except for external API calls
- Log errors with context
- Return None or False for failures (not exceptions)

### Testing
- Unit tests in `tests/` directory
- Property-based tests for core logic
- Test file naming: `test_*.py`
- Use pytest framework

## Import Paths

### From src/logic/
```python
# Correct
from action_type import AutoAction
from system_executor import SystemExecutor
from system_executor.ocr_engine import OCRFactory

# Also correct (relative)
from .action_type import AutoAction
from .system_executor import SystemExecutor
```

### From src/ui/
```python
# Correct
from logic.action_type import AutoAction
from logic.system_executor import SystemExecutor

# Also correct (relative)
from ..logic.action_type import AutoAction
from ..logic.system_executor import SystemExecutor
```

## When Adding New Features

1. **Determine if it's logic or UI**
   - Logic → `src/logic/`
   - UI → `src/ui/`

2. **If it's a new logic component**
   - Create in `src/logic/` or `src/logic/system_executor/`
   - Keep file size < 500 lines
   - Use single responsibility principle

3. **If it's a new UI component**
   - Create in `src/ui/`
   - Import logic from `src/logic/`
   - Keep business logic minimal

4. **Update imports**
   - Add to `__init__.py` if creating new package
   - Update wrapper files for backward compatibility

## Backward Compatibility

- **Wrapper file** `src/logic/system_executor.py` maintains old import paths
- Old code: `from system_executor import SystemExecutor` still works
- New code: `from system_executor.system_executor import SystemExecutor` also works
- Never break existing imports without migration plan

## Documentation

- Each module has docstring explaining purpose
- Each class has docstring with usage example
- Each public method has docstring with parameters and return value
- Complex logic has inline comments

## Performance Considerations

- Cache template matching results in `_last_match`
- Cache OCR engine instances
- Cache Gemini model instances
- Use adaptive ROI/scale for template matching
- Lazy initialization for expensive resources
