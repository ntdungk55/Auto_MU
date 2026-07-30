# Design Document: Multi-Image Algorithm Testing Dialog

## Overview

Dialog này cho phép user test nhiều window captures với teaching image để tìm preprocessing algorithm tốt nhất. Dialog sử dụng PyQt6 với layout 2-column cho preview, list widget cho window captures, và background threading cho testing.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  MultiImageAlgorithmTestingDialog (QDialog)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Preview Area (QSplitter - 50/50)                     │  │
│  │  ├─ Teaching Preview (QGraphicsView)                  │  │
│  │  └─ Window Capture Preview (QGraphicsView)            │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Window Captures List (QListWidget)                   │  │
│  │  - Checkbox items                                     │  │
│  │  - Show filename + match score                        │  │
│  │  - Buttons: Load, Capture, Remove                     │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Algorithm Management                                 │  │
│  │  - Dropdown + Add button                              │  │
│  │  - List with Settings/Delete buttons                  │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Testing Controls                                     │  │
│  │  - Algorithm dropdown                                 │  │
│  │  - Test/Stop buttons                                  │  │
│  │  - Progress bar                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│  [OK] [Close]                                               │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. MultiImageAlgorithmTestingDialog

**Class:** `MultiImageAlgorithmTestingDialog(QDialog)`

**Constructor:**
```python
def __init__(
    self,
    action: AutoAction,
    parent=None,
    target_window_hwnd: int = None,
    tool_id: str = None
)
```

**Key Attributes:**
- `action: AutoAction` - Action object chứa settings
- `target_window_hwnd: int` - Window handle để capture
- `tool_id: str` - UUID của tool
- `teaching_image_path: str` - Path đến teaching image
- `window_captures: list[str]` - List paths của window captures
- `test_results: dict[str, float]` - Dict {path: score}
- `algorithms: list[dict]` - List algorithm configs
- `testing_thread: threading.Thread` - Background test thread
- `stop_testing: bool` - Flag để stop test

**Signals (Thread-safe):**
```python
_test_progress_signal = pyqtSignal(int, str, float)  # (index, filename, score)
_test_complete_signal = pyqtSignal()
_test_error_signal = pyqtSignal(int, str, str)  # (index, filename, error)
```

### 2. Preview Components

**Teaching Preview:**
- `QGraphicsView` với `QGraphicsScene`
- Load teaching image từ `action.image_path`
- Scale to fit trong preview area
- Read-only (không cho phép interaction)

**Window Capture Preview:**
- `QGraphicsView` với `QGraphicsScene`
- Hiển thị window capture được chọn
- Highlight match region sau khi test (vẽ rectangle)
- Update khi user click vào item trong list

### 3. Window Captures List

**QListWidget với custom items:**
```python
class WindowCaptureItem(QListWidgetItem):
    - Checkbox (Qt.ItemIsUserCheckable)
    - Text: "filename | Match: 0.XX ✅/❌"
    - Data (UserRole): full path to image
```

**Buttons:**
- `load_btn`: Load nhiều ảnh từ local (QFileDialog.getOpenFileNames)
- `capture_btn`: Chụp ảnh mới từ window (WindowCapture.capture)
- `remove_btn`: Xóa các items đã chọn

### 4. Algorithm Management

**Hardcoded Algorithms:**
```python
DEFAULT_ALGORITHMS = [
    {"id": "none", "name": "None", "config": {}},
    {"id": "upscale_2x", "name": "Upscale 2x", "config": {"upscale": 2.0}},
    {"id": "upscale_contrast", "name": "Upscale+Contrast", 
     "config": {"upscale": 2.0, "enhance_contrast": True}},
    {"id": "upscale_contrast_sharpen", "name": "Upscale+Contrast+Sharpen",
     "config": {"upscale": 2.0, "enhance_contrast": True, "sharpen": True}},
    {"id": "full_pipeline", "name": "Full Pipeline",
     "config": {"upscale": 2.0, "enhance_contrast": True, "sharpen": True, "denoise": True}},
    {"id": "upscale_3x", "name": "Upscale 3x", "config": {"upscale": 3.0}},
    {"id": "upscale_3x_contrast_sharpen", "name": "Upscale 3x+Contrast+Sharpen",
     "config": {"upscale": 3.0, "enhance_contrast": True, "sharpen": True}},
]
```

**UI:**
- Dropdown để chọn algorithm
- Nút Add để thêm vào list
- List hiển thị algorithms với Settings/Delete buttons
- Settings button → Show message "Tính năng đang phát triển"

### 5. Testing Engine

**Method:** `_test_single_image(image_path: str, algorithm: dict) -> float`

**Flow:**
```python
1. Load teaching image từ action.image_path
2. Load window capture từ image_path
3. Apply preprocessing lên teaching image:
   - OCRPreprocessor(teaching_img)
   - .upscale() nếu có
   - .enhance_contrast() nếu có
   - .sharpen() nếu có
   - .denoise() nếu có
   - .build()
4. Convert cả 2 sang grayscale
5. Template matching:
   - Nếu multiscale_enabled: test nhiều scales
   - Ngược lại: single scale
   - cv2.matchTemplate(TM_CCOEFF_NORMED)
6. Return max score (0.0 - 1.0)
```

**Background Testing:**
```python
def _run_test_worker():
    for i, item in enumerate(checked_items):
        if stop_testing:
            break
        
        image_path = item.data(Qt.UserRole)
        score = _test_single_image(image_path, selected_algorithm)
        
        # Emit signal (thread-safe)
        _test_progress_signal.emit(i, filename, score)
    
    _test_complete_signal.emit()
```

## Data Models

### Action Fields (thêm vào AutoAction)

```python
class AutoAction:
    # ... existing fields ...
    
    # New fields for multi-image testing
    window_capture_paths: list[str] = []  # Paths to window captures
    window_capture_results: dict[str, float] = {}  # {path: score}
    preprocessing_algorithms: list[dict] = []  # Algorithm configs
```

### Algorithm Config Format

```python
{
    "id": "upscale_2x",  # Unique identifier
    "name": "Upscale 2x",  # Display name
    "config": {  # Preprocessing parameters
        "upscale": 2.0,
        "enhance_contrast": False,
        "sharpen": False,
        "denoise": False
    }
}
```

### Test Result Format

```python
{
    "images/tool_id/action_name/window_captures/capture_001.png": 0.92,
    "images/tool_id/action_name/window_captures/capture_002.png": 0.78,
    "images/tool_id/action_name/window_captures/capture_003.png": 0.95,
}
```

## File Management

### Auto-save Window Captures

**Folder Structure:**
```
images/
  [tool_id]/
    [action_name]/
      window_captures/
        capture_001.png
        capture_002.png
        capture_003.png
```

**Naming Convention:**
- Format: `capture_XXX.png` (XXX = 001, 002, 003, ...)
- Tìm số lớn nhất hiện có và +1

**Save Logic:**
```python
def _get_next_capture_filename() -> str:
    folder = f"images/{tool_id}/{action_name}/window_captures/"
    os.makedirs(folder, exist_ok=True)
    
    existing = [f for f in os.listdir(folder) if f.startswith("capture_")]
    if not existing:
        return os.path.join(folder, "capture_001.png")
    
    # Find max number
    numbers = [int(f.split("_")[1].split(".")[0]) for f in existing]
    next_num = max(numbers) + 1
    return os.path.join(folder, f"capture_{next_num:03d}.png")
```

## Error Handling

### Teaching Image Not Found
```python
if not os.path.exists(teaching_image_path):
    QMessageBox.warning(self, "Cảnh báo", 
        "Teaching image không tồn tại!\nVui lòng chọn teaching image trước.")
    self.test_btn.setEnabled(False)
    self.load_btn.setEnabled(False)
    self.capture_btn.setEnabled(False)
```

### Window Capture Failed
```python
try:
    screenshot = WindowCapture.capture(hwnd)
    if screenshot is None:
        raise Exception("Capture returned None")
except Exception as e:
    QMessageBox.critical(self, "Lỗi", f"Không thể chụp screenshot: {e}")
```

### Test Error
```python
try:
    score = _test_single_image(path, algorithm)
except Exception as e:
    _test_error_signal.emit(index, filename, str(e))
    score = -1.0  # Mark as error
```

## Testing Strategy

### Unit Tests

**File:** `tests/test_multi_image_algorithm_testing.py`

**Test Cases:**
1. `test_dialog_initialization()` - Dialog khởi tạo đúng với action
2. `test_load_teaching_image()` - Load teaching image từ action.image_path
3. `test_add_window_capture()` - Thêm window capture vào list
4. `test_remove_window_capture()` - Xóa window capture khỏi list
5. `test_algorithm_management()` - Add/delete algorithms
6. `test_preprocessing_application()` - Apply preprocessing đúng
7. `test_template_matching()` - Template matching trả về score đúng
8. `test_save_on_ok()` - Click OK lưu data vào action
9. `test_cancel_on_close()` - Click Close không lưu data
10. `test_data_persistence()` - Save tool → reload → verify data

### Manual Test Plan

**File:** `docs/MANUAL_TEST_MULTI_IMAGE_ALGORITHM_TESTING.md`

**Test Scenarios:**
1. Open dialog từ Passive Read Settings
2. Load multiple window captures
3. Capture new screenshot
4. Select window capture → verify preview
5. Test với algorithm → verify results
6. Check best score marked with ⭐
7. Add/delete algorithms
8. Click OK → verify data saved
9. Click Close → verify data not saved
10. Reopen dialog → verify data loaded

## Thread-Safe UI Updates

### Pattern

```python
class MultiImageAlgorithmTestingDialog(QDialog):
    # Define signals
    _test_progress_signal = pyqtSignal(int, str, float)
    _test_complete_signal = pyqtSignal()
    _test_error_signal = pyqtSignal(int, str, str)
    
    def __init__(self, ...):
        super().__init__(...)
        # Connect signals with QueuedConnection
        self._test_progress_signal.connect(
            self._on_test_progress, 
            Qt.ConnectionType.QueuedConnection
        )
        self._test_complete_signal.connect(
            self._on_test_complete,
            Qt.ConnectionType.QueuedConnection
        )
        self._test_error_signal.connect(
            self._on_test_error,
            Qt.ConnectionType.QueuedConnection
        )
    
    def _run_test(self):
        """Start test in background thread."""
        def worker():
            # Background work
            for i, item in enumerate(checked_items):
                score = _test_single_image(...)
                # Emit signal (thread-safe)
                self._test_progress_signal.emit(i, filename, score)
            self._test_complete_signal.emit()
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def _on_test_progress(self, index: int, filename: str, score: float):
        """ALWAYS called from UI thread via signal."""
        item = self.list_widget.item(index)
        item.setText(f"{filename} | Match: {score:.2f}")
    
    def _on_test_complete(self):
        """ALWAYS called from UI thread via signal."""
        self.test_btn.setEnabled(True)
        self._highlight_best_score()
```

## Data Persistence

### Serialize (tool_manager.py)

```python
def _action_to_dict(action: AutoAction) -> dict:
    d = {
        # ... existing fields ...
        "window_capture_paths": action.window_capture_paths or [],
        "window_capture_results": action.window_capture_results or {},
        "preprocessing_algorithms": action.preprocessing_algorithms or [],
    }
    return d
```

### Deserialize (tool_manager.py)

```python
@staticmethod
def from_dict(d: dict) -> AutoAction:
    action = AutoAction(...)
    # ... existing fields ...
    action.window_capture_paths = d.get("window_capture_paths", [])
    action.window_capture_results = d.get("window_capture_results", {})
    action.preprocessing_algorithms = d.get("preprocessing_algorithms", [])
    return action
```

### Verification Checklist

1. ✅ Add fields to AutoAction class
2. ✅ Save to action in `get_settings()` method (dialog's accept())
3. ✅ Load from action in `_load_settings()` method (dialog's __init__)
4. ✅ Serialize in `_action_to_dict()` in tool_manager.py
5. ✅ Deserialize in `from_dict()` in tool_manager.py
6. ✅ Test: Save → Close app → Reopen → Verify data persists

## Performance Considerations

### Image Loading
- Cache loaded images trong memory
- Dùng cv2.imdecode cho Unicode paths
- Scale images cho preview (không load full size)

### Template Matching
- Chạy trong background thread
- Có thể stop bất cứ lúc nào
- Progress bar update mỗi image

### Memory Management
- Giới hạn 50 window captures
- Clear cache khi đóng dialog
- Không giữ full-size images trong memory

## Integration Points

### PassiveReadSettingsDialog

Thêm nút mở dialog:

```python
# In teaching_group section
test_algo_btn = QPushButton("🧪 Test Algorithms")
test_algo_btn.clicked.connect(self._open_algorithm_testing_dialog)
teaching_layout.addWidget(test_algo_btn)

def _open_algorithm_testing_dialog(self):
    from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    dialog = MultiImageAlgorithmTestingDialog(
        self.action,
        parent=self,
        target_window_hwnd=self.target_window_hwnd,
        tool_id=self.tool_id
    )
    if dialog.exec():
        # Data already saved to action in dialog
        pass
```

## UI Layout Details

### Window Size
- Fixed size: 1000x700 pixels
- Resizable: No (để đơn giản)

### Preview Area
- QSplitter với 2 QGraphicsView
- Split 50/50
- Teaching bên trái, Window capture bên phải
- Scale images to fit

### List Widget
- Height: ~200 pixels
- Scrollable
- Checkbox items
- Single selection

### Buttons Layout
```
[OK]  [Close]
```
- OK: Lưu và đóng (accept())
- Close: Không lưu và đóng (reject())
