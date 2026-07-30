---
inclusion: auto
---

# Coding Guidelines

## General Principles

### 1. Minimal Code
- Write only the **absolute minimum** code needed
- Avoid verbose implementations
- Remove dead code immediately
- Don't over-engineer solutions

### 2. Builder Pattern
- Use for complex object construction
- Fluent interface with method chaining
- Example: `OCRPreprocessor(img).upscale(2.0).enhance_contrast().sharpen().build()`

### 3. Factory Pattern
- Use for object creation with multiple implementations
- Example: `OCRFactory.create("auto")` returns appropriate OCR engine

### 4. Single Responsibility
- Each class does ONE thing well
- Each method does ONE thing well
- If a method is > 50 lines, consider splitting

### 5. No Mocking in Tests
- KHÔNG dùng mock cho đối tượng đang được test (subject under test)
- Có thể dùng mock cho external dependencies: API calls, database, file system, hardware
- Property-based tests generate many inputs

## Python Specific

### Type Hints
```python
# Always use type hints
def process_image(img: np.ndarray, threshold: float = 0.8) -> tuple[str, float]:
    """Process image and return (text, confidence)."""
    pass

# For complex types
from typing import Optional, Dict, List
def find_matches(templates: Dict[str, np.ndarray]) -> Optional[List[tuple]]:
    pass
```

### Docstrings
```python
def method_name(param1: str, param2: int) -> bool:
    """Short description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When something is wrong
    """
    pass
```

### Error Handling
```python
# Good: Return None/False for expected failures
def find_image(path: str) -> Optional[tuple]:
    try:
        img = cv2.imread(path)
        if img is None:
            return None
        return process(img)
    except Exception as e:
        self._ui_log(f"Error: {e}")
        return None

# Bad: Raise exceptions for expected failures
def find_image(path: str) -> tuple:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Image not found: {path}")
    return process(img)
```

### Logging
```python
# Use self._ui_log() for user-facing messages
self._ui_log(f"<b style='color:green;'>[Success]</b> Found image")
self._ui_log(f"<b style='color:red;'>[Error]</b> Failed to process")

# Use print() for debug messages
print(f"[DEBUG] Processing image: {path}")
```

### Thread-Safe UI Updates (CRITICAL!)
```python
# ❌ BAD: Direct UI update from background thread (WILL CRASH!)
def background_task():
    # This runs in background thread
    self.text_widget.append("Log message")  # CRASH!

# ✅ GOOD: Use signals for thread-safe UI updates
class MyWindow(QMainWindow):
    # Define signal
    _log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        # Connect signal with QueuedConnection (thread-safe)
        self._log_signal.connect(self._append_log, Qt.ConnectionType.QueuedConnection)
    
    def _append_log(self, msg: str):
        """ALWAYS called from UI thread via signal."""
        self.text_widget.append(msg)
    
    def _log(self, msg: str):
        """Thread-safe: can be called from any thread."""
        self._log_signal.emit(msg)  # Emit signal instead of direct update
    
    def background_task(self):
        # This runs in background thread
        self._log("Log message")  # Safe! Uses signal

# Why this works:
# 1. background_task() calls _log() which emits signal
# 2. Qt queues the signal in UI thread's event loop
# 3. UI thread processes signal and calls _append_log()
# 4. _append_log() updates UI safely (always in UI thread)
```

**Rules:**
- ⛔ **NEVER** update UI widgets directly from background threads
- ⛔ **NEVER** call QWidget methods (setText, append, etc.) from non-UI threads
- ✅ **ALWAYS** use signals with QueuedConnection for cross-thread UI updates
- ✅ **ALWAYS** emit signals from background threads, process in UI thread
- ✅ Pattern: `background_thread → emit signal → Qt queue → UI thread → update widget`

**Common UI widgets that need thread-safe updates:**
- QTextEdit.append()
- QLabel.setText()
- QTableWidget.setItem()
- QProgressBar.setValue()
- Any QWidget method that modifies UI

## File Size Guidelines

| Component | Max Lines | Typical |
|-----------|-----------|---------|
| Logic module | 500 | 300-400 |
| UI component | 400 | 200-300 |
| Test file | 300 | 150-250 |
| Package __init__ | 50 | 20-30 |

## Import Organization

```python
# 1. Standard library
import os
import sys
import time
from datetime import datetime
from typing import Optional, Dict

# 2. Third-party
import cv2
import numpy as np
from PyQt5.QtWidgets import QDialog

# 3. Local - absolute
from action_type import AutoAction, ActionType

# 4. Local - relative
from .ocr_engine import OCRFactory
from ..action_type import AutoAction
```

## Naming Conventions

### Variables & Functions
```python
# snake_case for variables and functions
image_path = "path/to/image.png"
template_cache = {}

def process_image(img: np.ndarray) -> np.ndarray:
    pass

def _private_helper():
    pass
```

### Classes
```python
# PascalCase for classes
class SystemExecutor:
    pass

class OCRPreprocessor:
    pass
```

### Constants
```python
# UPPER_CASE for constants
MOUSEEVENTF_LEFTDOWN = 0x0002
DEFAULT_THRESHOLD = 0.8
MAX_RETRIES = 3
```

### Private Members
```python
class MyClass:
    def __init__(self):
        self._private_var = None      # Private variable
        self.__very_private = None    # Name mangling
    
    def public_method(self):
        pass
    
    def _private_method(self):
        pass
```

## Common Patterns

### Builder Pattern
```python
class OCRPreprocessor:
    def __init__(self, img: np.ndarray):
        self.img = img.copy()
    
    def upscale(self, factor: float = 2.0) -> 'OCRPreprocessor':
        self.img = cv2.resize(self.img, None, fx=factor, fy=factor)
        return self
    
    def enhance_contrast(self) -> 'OCRPreprocessor':
        # Process
        return self
    
    def build(self) -> np.ndarray:
        return self.img

# Usage
result = OCRPreprocessor(img).upscale(2.0).enhance_contrast().build()
```

### Factory Pattern
```python
class OCRFactory:
    @staticmethod
    def create(engine_type: str) -> OCREngine:
        if engine_type == "winrt":
            return WinRTOCREngine()
        elif engine_type == "tesseract":
            return TesseractOCREngine()
        else:
            return TesseractOCREngine()  # Default

# Usage
engine = OCRFactory.create("auto")
text = engine.recognize(img)
```

### Lazy Initialization
```python
class SystemExecutor:
    def __init__(self):
        self._ocr_engine = None
    
    def _get_ocr_engine(self):
        if self._ocr_engine is None:
            self._ocr_engine = OCRFactory.create("auto")
        return self._ocr_engine
```

### Caching
```python
class TemplateMatcher:
    def __init__(self):
        self._template_cache = {}
    
    def _load_template(self, path: str) -> np.ndarray:
        if path in self._template_cache:
            return self._template_cache[path]
        
        img = cv2.imread(path)
        self._template_cache[path] = img
        return img
```

## Testing Guidelines

### Unit Tests
```python
def test_ocr_preprocessor_upscale():
    """Test that upscale increases image size."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = OCRPreprocessor(img).upscale(2.0).build()
    
    assert result.shape[0] == 200
    assert result.shape[1] == 200

def test_find_image_returns_none_when_not_found():
    """Test that find_image returns None when template not found."""
    executor = SystemExecutor(hwnd)
    result = executor.find_image("nonexistent.png")
    
    assert result is None
```

### Property-Based Tests
```python
from hypothesis import given
import hypothesis.strategies as st

@given(st.integers(min_value=1, max_value=10))
def test_upscale_factor_valid(factor):
    """Test upscale works with any valid factor."""
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    result = OCRPreprocessor(img).upscale(float(factor)).build()
    
    assert result.shape[0] == int(100 * factor)
    assert result.shape[1] == int(100 * factor)
```

## Performance Tips

### Caching
- Cache template grayscale conversions
- Cache scaled templates
- Cache last match positions
- Cache OCR engine instances

### Optimization
- Use adaptive ROI for template matching
- Prefer last used scale first
- Early exit when threshold met
- Lazy initialization for expensive resources

### Profiling
```python
import time

start = time.perf_counter()
# Code to profile
elapsed = (time.perf_counter() - start) * 1000
print(f"Took {elapsed:.1f}ms")
```

## Common Mistakes to Avoid

### ❌ Don't
```python
# Over-engineering
class ComplexProcessor:
    def __init__(self, config: Dict):
        self.config = config
        self.state = {}
        self.cache = {}
        # 100 lines of initialization

# Mocking the subject under test
def test_something():
    mock_engine = Mock()
    mock_engine.recognize.return_value = "text"
    # Nếu OCREngine là thứ đang test → không được mock nó
    # (OK nếu mock external dep như HTTP client, hardware)

# Negative statements
def should_not_crash():
    pass

# Vague error handling
try:
    process()
except:
    pass
```

### ✅ Do
```python
# Simple and focused
class Processor:
    def process(self, img: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Real tests
def test_ocr_recognizes_text():
    engine = TesseractOCREngine()
    text = engine.recognize(img)
    assert len(text) > 0

# Positive statements
def should_process_successfully():
    pass

# Specific error handling
try:
    process()
except FileNotFoundError as e:
    self._ui_log(f"File not found: {e}")
    return None
except Exception as e:
    self._ui_log(f"Unexpected error: {e}")
    return None
```

## Code Review Checklist

- [ ] Single responsibility principle followed
- [ ] Type hints present for all functions
- [ ] Docstrings for public methods
- [ ] No dead code
- [ ] Error handling appropriate
- [ ] Logging messages clear
- [ ] File size < 500 lines
- [ ] No mocking the subject under test (mock external deps is OK)
- [ ] Imports organized correctly
- [ ] Naming conventions followed
- [ ] **Thread-safe UI updates (signals for cross-thread communication)**
