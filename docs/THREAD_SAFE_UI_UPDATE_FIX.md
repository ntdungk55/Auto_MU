# Thread-Safe UI Update Fix - EVENT_NOTIFY Crash Bug

## 📋 Tóm tắt

**Bug:** App crash khi click "Dừng" liên tục trong TEST mode với EVENT_NOTIFY action  
**Root cause:** Direct UI update từ background thread (race condition)  
**Solution:** Sử dụng Qt signals với QueuedConnection cho thread-safe UI updates  
**Status:** ✅ Fixed  
**Commits:**
- `9b3e139` - [Fix] Option 1 - Use signal for thread-safe logging in TEST mode
- `691a485` - [Docs] Add thread-safe UI update rules to project guidelines

---

## 🐛 Mô tả Bug

### Triệu chứng:
- Click "▶ Chạy" để test EVENT_NOTIFY action
- Click "■ Dừng" LIÊN TỤC nhiều lần (spam click)
- App crash ngay lập tức

### Điều kiện:
- Chỉ xảy ra trong **TEST mode** (tool_editor_window.py)
- Chỉ xảy ra khi click "Dừng" liên tục
- **KHÔNG** xảy ra khi chạy tool bình thường (main.py)

### Quan sát quan trọng:
> "chạy thật thì không làm sao mà chạy TEST lại gặp vấn đề"

Điều này là manh mối quan trọng để tìm ra sự khác biệt giữa TEST mode và NORMAL run.

---

## 🔍 Root Cause Analysis

### So sánh TEST mode vs NORMAL run:

| Aspect | TEST Mode | NORMAL Run |
|--------|-----------|------------|
| Engine | `_TestEngine` (mock, simple) | `AutoBotEngine` (full-featured) |
| Logging | `_log()` → **direct UI update** | `_log()` → **signal emit** |
| Thread safety | ❌ NOT thread-safe | ✅ Thread-safe |
| Connection | Direct method call | QueuedConnection signal |

### Vấn đề cụ thể:

**TEST mode (`tool_editor_window.py`):**
```python
def _log(self, msg: str):
    """Direct UI update - NOT thread-safe!"""
    self.test_log_area.append(msg)  # ❌ Called from background thread
```

**NORMAL run (`main.py`):**
```python
def _log(self, msg: str):
    """Thread-safe via signal."""
    self.log_signal.emit(msg)  # ✅ Emit signal, Qt handles threading
```

### Race condition:

1. User clicks "▶ Chạy" → Background thread starts
2. Background thread calls `_log()` → Updates `QTextEdit` directly
3. User clicks "■ Dừng" → UI thread calls `_log()` → Updates `QTextEdit` directly
4. **2 threads cùng update QTextEdit** → **CRASH!**

Qt widgets are **NOT thread-safe**. Chỉ UI thread mới được phép update widgets.

---

## ✅ Solution: Signal-Based Logging

### Implementation:

```python
class ToolEditorWindow(QMainWindow):
    # 1. Define signal
    _test_log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        # 2. Connect signal with QueuedConnection (thread-safe)
        self._test_log_signal.connect(self._append_log, Qt.ConnectionType.QueuedConnection)
    
    def _append_log(self, msg: str):
        """ALWAYS called from UI thread via signal.
        
        This method is connected to _test_log_signal with QueuedConnection,
        ensuring it's always executed in the UI thread, making it thread-safe.
        """
        # Add timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"<span style='color:#888;'>[{timestamp}]</span> {msg}"
        
        # Append to test log area (safe because always called from UI thread)
        self.test_log_area.append(formatted_msg)
        
        # Auto-scroll to bottom
        cursor = self.test_log_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.test_log_area.setTextCursor(cursor)
    
    def _log(self, msg: str):
        """Log message to test log area (thread-safe via signal).
        
        This method emits a signal instead of directly updating the UI,
        making it safe to call from any thread (UI thread or background thread).
        """
        self._test_log_signal.emit(msg)  # 3. Emit signal
```

### Cách hoạt động:

```
Background Thread                Qt Event Queue              UI Thread
─────────────────                ──────────────              ─────────
_log("message")
    │
    └─> emit signal ──────────> Queue signal ──────────> _append_log("message")
                                                              │
                                                              └─> Update QTextEdit
```

1. Background thread gọi `_log()` → emit signal
2. Qt queue signal vào UI thread's event loop
3. UI thread xử lý signal → gọi `_append_log()`
4. `_append_log()` update UI safely (luôn trong UI thread)

### Tại sao QueuedConnection quan trọng:

- **DirectConnection:** Signal handler chạy trong thread của sender (KHÔNG thread-safe!)
- **QueuedConnection:** Signal handler chạy trong thread của receiver (thread-safe!)
- **AutoConnection:** Qt tự chọn (Direct nếu cùng thread, Queue nếu khác thread)

Trong trường hợp này, ta dùng **QueuedConnection** để đảm bảo `_append_log()` LUÔN chạy trong UI thread.

---

## 🧪 Testing

### Test case:
1. Mở tool có EVENT_NOTIFY action
2. Click "Sửa" để mở Tool Editor
3. Click "▶ Chạy" để test action
4. Click "■ Dừng" LIÊN TỤC nhiều lần (spam click)

### Kết quả:
- ✅ App không crash
- ✅ Log messages hiển thị bình thường
- ✅ UI responsive

---

## 📚 Lessons Learned

### 1. Qt Threading Rules:
- ⛔ **NEVER** update UI widgets từ background threads
- ⛔ **NEVER** gọi QWidget methods (setText, append, etc.) từ non-UI threads
- ✅ **ALWAYS** dùng signals với QueuedConnection cho cross-thread UI updates

### 2. Common UI widgets cần thread-safe:
- `QTextEdit.append()`
- `QLabel.setText()`
- `QTableWidget.setItem()`
- `QProgressBar.setValue()`
- Bất kỳ QWidget method nào modify UI

### 3. Pattern chuẩn:
```python
# 1. Define signal
signal_name = pyqtSignal(arg_types)

# 2. Connect with QueuedConnection
signal_name.connect(handler, Qt.ConnectionType.QueuedConnection)

# 3. Emit from any thread
signal_name.emit(data)

# 4. Handler always runs in UI thread
def handler(data):
    self.widget.update(data)  # Safe!
```

### 4. Debugging tips:
- So sánh code giữa working và broken versions
- Tìm sự khác biệt về threading
- Test bằng cách spam click để trigger race conditions
- Dùng print() để trace thread execution

---

## 📝 Project Guidelines Updated

Đã thêm rules vào:

### 1. `coding-guidelines.md`:
- Section "Thread-Safe UI Updates (CRITICAL!)"
- Code examples với ❌ BAD và ✅ GOOD patterns
- Giải thích chi tiết về signals và QueuedConnection

### 2. `00-MASTER-RULES.md`:
- Section 6: "THREAD-SAFE UI UPDATES (CRITICAL!)"
- Thêm vào checklist "Trước khi commit"
- Thêm vào "COMPLIANCE VERIFICATION"
- Thêm vào "TÓM TẮT NGẮN GỌN"

---

## 🎯 Takeaway

**Khi làm việc với PyQt và threading:**
1. Luôn nhớ: **UI widgets are NOT thread-safe**
2. Dùng signals cho cross-thread communication
3. Test bằng cách spam click để phát hiện race conditions
4. So sánh với code working để tìm sự khác biệt

**Pattern đơn giản:**
```
Background thread → emit signal → Qt queue → UI thread → update widget
```

**Khi nghi ngờ → Dùng signals!** 🚀

---

## 📎 Related Files

- `src/ui/tool_editor_window.py` - Fixed implementation
- `docs/TEST_VS_NORMAL_COMPARISON.md` - Detailed analysis
- `.kiro/steering/coding-guidelines.md` - Thread-safe UI rules
- `.kiro/steering/00-MASTER-RULES.md` - Master rules updated
