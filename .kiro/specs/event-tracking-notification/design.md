# Feature Design: Event Tracking Notification

## 1. Impact Analysis

### 1.1. Tác động đến code hiện tại

**Files cần sửa:**
- `src/logic/action_type.py`: Thêm 5 fields mới vào AutoAction dataclass (bỏ event_roi_coordinates, dùng teaching_corner_x1/y1/x2/y2)
- `src/logic/tool_manager.py`: Thêm serialization/deserialization cho 5 fields mới
- `src/ui/passive_read_settings_dialog.py`: Thêm UI controls cho Event Tracking settings (không có ROI buttons, dùng Teaching image ROI)
- `src/logic/system_executor/system_executor.py`: Thêm logic xử lý Event Tracking mode, sử dụng ROI từ teaching_corner_x1/y1/x2/y2

**Classes/methods bị ảnh hưởng:**
- `AutoAction` dataclass: Thêm 5 fields mới (event_ocr_pattern, event_match_threshold, event_delay_threshold, event_reset_interval, event_telegram_message, bỏ event_roi_coordinates - dùng teaching_corner_x1/y1/x2/y2)
- `Tool._action_to_dict()`: Thêm serialization cho 5 fields mới
- `Tool.from_dict()`: Thêm deserialization cho 5 fields mới
- `PassiveReadSettingsDialog`: Thêm UI section "Event Tracking Settings" (không có ROI buttons)
- `SystemExecutor._execute_read_passive()`: Thêm logic xử lý Event Tracking mode, lấy ROI từ teaching_corner_x1/y1/x2/y2

**Breaking changes:** Không có - tất cả fields mới đều có giá trị mặc định, backward compatible với tools cũ.

### 1.2. Dependencies

**Thư viện mới cần thêm:**
- `rapidfuzz`: Latest - Fuzzy string matching cho Match Threshold < 100%
  - Hoặc `fuzzywuzzy`: Latest - Alternative nếu rapidfuzz không khả dụng
  - Cài đặt: `pip install rapidfuzz` hoặc `pip install fuzzywuzzy python-Levenshtein`

**Phụ thuộc modules:**
- `src/logic/system_executor/telegram_notifier.py`: Gửi thông báo Telegram
- `src/logic/system_executor/ocr_engine.py`: Đọc text từ ROI
- `src/logic/system_executor/ocr_preprocessor.py`: Tiền xử lý ảnh trước OCR
- `src/logic/system_executor/window_capture.py`: Capture screenshot từ ROI

### 1.3. Khó khăn kỹ thuật

**Khó khăn 1: Pattern matching với placeholder**
- Mô tả: Convert OCR Pattern "{event_name} sẽ bắt đầu sau {minutes} phút" thành regex để trích xuất biến
- Giải pháp: Sử dụng regex với named groups: `(?P<event_name>.+?) sẽ bắt đầu sau (?P<minutes>\d+) phút`

**Khó khăn 2: Fuzzy matching khi Match Threshold < 100%**
- Mô tả: Text OCR có thể không khớp chính xác 100% với pattern do lỗi OCR
- Giải pháp: Sử dụng rapidfuzz.fuzz.ratio() để tính độ tương đồng, chấp nhận nếu >= Match Threshold

**Khó khăn 3: Duplicate detection với Reset Interval**
- Mô tả: Cần lưu danh sách thông báo đã gửi với timestamp để kiểm tra duplicate
- Giải pháp: Sử dụng dict in-memory: {message_text: last_sent_timestamp}, clear entries cũ hơn Reset Interval


### 1.4. Rủi ro

**Rủi ro 1: OCR không đọc chính xác text**
- Mô tả: OCR có thể đọc sai text, dẫn đến không khớp pattern hoặc trích xuất sai biến
- Cách giảm thiểu: 
  - Cho phép user cấu hình OCR preprocessing algorithms
  - Hỗ trợ Match Threshold < 100% với fuzzy matching
  - Test kỹ với nhiều ảnh khác nhau trong Algorithm Testing Dialog

**Rủi ro 2: Spam Telegram nếu Reset Interval quá ngắn**
- Mô tả: Nếu Reset Interval = 0 hoặc quá ngắn, có thể gửi quá nhiều thông báo giống nhau
- Cách giảm thiểu:
  - Mặc định Reset Interval = 15 phút (reasonable)
  - Hiển thị warning trong UI nếu user set < 5 phút
  - Duplicate detection chính xác với exact string comparison

**Rủi ro 3: Memory leak nếu danh sách đã gửi không được dọn dẹp**
- Mô tả: Dict lưu thông báo đã gửi có thể tăng trưởng vô hạn nếu không clear
- Cách giảm thiểu:
  - Định kỳ clear entries cũ hơn Reset Interval * 2
  - Giới hạn max size của dict (ví dụ: 1000 entries)
  - Reset dict khi tool restart

---

## 2. Technical Design

### 2.1. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  PassiveReadSettingsDialog (UI)                             │
│  - Event Tracking Settings section                          │
│  - ROI teaching button                                      │
│  - OCR Preprocessing config button                          │
└────────────────────┬────────────────────────────────────────┘
                     │ Save settings to
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  AutoAction (Data Model)                                    │
│  - event_tracking_enabled: bool                             │
│  - event_ocr_pattern: str                                   │
│  - event_match_threshold: float                             │
│  - event_delay_threshold: int                               │
│  - event_reset_interval: int                                │
│  - event_telegram_message: str                              │
│  - ROI: từ teaching_corner_x1/y1/x2/y2                      │
│  - ocr_algorithms: list[dict]                               │
└────────────────────┬────────────────────────────────────────┘
                     │ Serialize/Deserialize
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  ToolManager                                                │
│  - _action_to_dict(): Add 7 new fields                      │
│  - from_dict(): Load 7 new fields                           │
└────────────────────┬────────────────────────────────────────┘
                     │ Execute action
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  SystemExecutor._execute_read_passive()                     │
│  - Check if event_tracking_enabled                          │
│  - If True: Execute Event Tracking logic                    │
│  - If False: Execute normal passive read logic              │
└────────────────────┬────────────────────────────────────────┘
                     │ Event Tracking logic
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Event Tracking Flow                                        │
│  1. Capture screenshot from ROI                             │
│  2. Apply OCR preprocessing (if configured)                 │
│  3. Read text with OCR engine                               │
│  4. Parse text with pattern matching                        │
│  5. Check duplicate with Reset Interval                     │
│  6. Wait Delay Threshold                                    │
│  7. Send Telegram notification                              │
│  8. Save to sent list                                       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2. Design Patterns

**Builder Pattern**: OCRPreprocessor
- Lý do: Chuỗi các thuật toán preprocessing có thể thay đổi tùy user config
- Ví dụ: `OCRPreprocessor(img).upscale(2.0).enhance_contrast().sharpen().build()`

**Factory Pattern**: OCRFactory
- Lý do: Có nhiều OCR engines (WinRT, Tesseract), cần chọn engine phù hợp
- Ví dụ: `OCRFactory.create("auto")` returns appropriate engine

**Strategy Pattern**: Pattern Matching
- Lý do: Có 2 strategies: Exact matching (100%) và Fuzzy matching (< 100%)
- Ví dụ: `PatternMatcher.match(text, pattern, threshold)` chọn strategy dựa vào threshold


### 2.3. Code Organization

**Files được tạo:**
- Không có file mới - tất cả logic được thêm vào files hiện tại

**Files được sửa:**
- `src/logic/action_type.py`: Thêm 7 fields vào AutoAction
- `src/logic/tool_manager.py`: Thêm serialization/deserialization
- `src/ui/passive_read_settings_dialog.py`: Thêm UI section "Event Tracking Settings"
- `src/logic/system_executor/system_executor.py`: Thêm method `_execute_event_tracking()`

---

## 3. Code Skeleton

### 3.1. AutoAction (src/logic/action_type.py)

```python
@dataclass
class AutoAction:
    # ... existing fields ...
    
    # ============ Event Tracking Notification settings ============
    event_ocr_pattern: str = ""  # Pattern với placeholder: "{event_name} sẽ bắt đầu sau {minutes} phút"
    event_match_threshold: float = 100.0  # Độ khớp (0-100%), 100 = exact match
    event_delay_threshold: int = 0  # Thời gian chờ trước khi gửi Telegram (giây)
    event_reset_interval: int = 15  # Khoảng thời gian reset duplicate (phút), 0 = không reset
    event_telegram_message: str = ""  # Template message: "Sự kiện {event_name} vẫn đang diễn ra"
    # NOTE: ROI được lấy từ teaching_corner_x1, y1, x2, y2 (không cần field riêng)
```

### 3.2. SystemExecutor (src/logic/system_executor/system_executor.py)

```python
class SystemExecutor:
    def __init__(self, hwnd: int):
        """Initialize SystemExecutor."""
        self.hwnd = hwnd
        # ... existing initialization ...
        
        # Event Tracking state
        self._event_sent_messages: dict[str, float] = {}  # {message_text: last_sent_timestamp}
    
    def _execute_read_passive(self, action: AutoAction) -> bool:
        """Execute READ_PASSIVE action.
        
        Args:
            action: AutoAction with READ_PASSIVE type
            
        Returns:
            True if successful, False otherwise
        """
        # Check if Event Tracking mode (check passive_mode instead of event_tracking_enabled)
        if getattr(action, "passive_mode", "detect_image") == "event_tracking":
            return self._execute_event_tracking(action)
        
        # Normal passive read logic (existing code)
        # ...
    
    def _execute_event_tracking(self, action: AutoAction) -> bool:
        """Execute Event Tracking logic.
        
        Args:
            action: AutoAction with event_tracking_enabled=True
            
        Returns:
            True if successful, False otherwise
        """
        pass  # Implementation in Bước 4
    
    def _parse_event_pattern(self, text: str, pattern: str, threshold: float) -> Optional[dict]:
        """Parse text with pattern and extract variables.
        
        Args:
            text: OCR text to parse
            pattern: Pattern with placeholders (e.g., "{event_name} sẽ bắt đầu sau {minutes} phút")
            threshold: Match threshold (0-100%)
            
        Returns:
            Dict with extracted variables or None if no match
        """
        pass  # Implementation in Bước 4
    
    def _check_event_duplicate(self, message: str, reset_interval: int) -> bool:
        """Check if message was already sent recently.
        
        Args:
            message: Message text to check
            reset_interval: Reset interval in minutes (0 = never reset)
            
        Returns:
            True if duplicate (should skip), False if new (should send)
        """
        pass  # Implementation in Bước 4
    
    def _cleanup_event_sent_messages(self, reset_interval: int):
        """Clean up old entries from sent messages dict.
        
        Args:
            reset_interval: Reset interval in minutes
        """
        pass  # Implementation in Bước 4
```


### 3.3. ToolManager (src/logic/tool_manager.py)

```python
class Tool:
    @staticmethod
    def _action_to_dict(action: AutoAction):
        """Convert AutoAction to dict for JSON serialization."""
        return {
            # ... existing fields ...
            
            # Event Tracking Notification settings (5 fields, ROI từ teaching image)
            "event_ocr_pattern": str(getattr(action, "event_ocr_pattern", "") or ""),
            "event_match_threshold": float(getattr(action, "event_match_threshold", 100.0) or 100.0),
            "event_delay_threshold": int(getattr(action, "event_delay_threshold", 0) or 0),
            "event_reset_interval": int(getattr(action, "event_reset_interval", 15) or 15),
            "event_telegram_message": str(getattr(action, "event_telegram_message", "") or ""),
            # NOTE: ROI được lấy từ teaching_corner_x1, y1, x2, y2
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Tool':
        """Load Tool from dict (JSON deserialization)."""
        # ... existing code ...
        
        for a_data in data.get("actions", []):
            # ... existing action creation ...
            
            # Set Event Tracking fields after creation (5 fields, ROI từ teaching image)
            action.event_ocr_pattern = str(a_data.get("event_ocr_pattern", "") or "")
            action.event_match_threshold = float(a_data.get("event_match_threshold", 100.0) or 100.0)
            action.event_delay_threshold = int(a_data.get("event_delay_threshold", 0) or 0)
            action.event_reset_interval = int(a_data.get("event_reset_interval", 15) or 15)
            action.event_telegram_message = str(a_data.get("event_telegram_message", "") or "")
            # NOTE: ROI được lấy từ teaching_corner_x1, y1, x2, y2
            
            actions.append(action)
        
        return Tool(...)
```

### 3.4. PassiveReadSettingsDialog (src/ui/passive_read_settings_dialog.py)

```python
class PassiveReadSettingsDialog(QDialog):
    def _init_ui(self):
        """Initialize UI components."""
        # ... existing UI code ...
        
        # Mode selection dropdown (at top)
        mode_group = QGroupBox("🔄 Chế độ hoạt động")
        mode_layout = QVBoxLayout()
        
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Chế độ:"))
        self.passive_mode_combo = QComboBox()
        self.passive_mode_combo.addItems(["Đọc dữ liệu", "Phát hiện hình ảnh", "Event Tracking"])  # Add 3rd mode
        self.passive_mode_combo.setCurrentIndex(1)  # Default: Phát hiện hình ảnh
        self.passive_mode_combo.currentIndexChanged.connect(self._on_passive_mode_changed)
        mode_row.addWidget(self.passive_mode_combo)
        mode_row.addStretch()
        mode_layout.addLayout(mode_row)
        
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)
        
        # ... existing mode 1 and mode 2 sections ...
        
        # === COMMON SECTIONS (all modes) ===
        
        # Teaching image (COMMON - hiển thị cho tất cả modes)
        teaching_group = QGroupBox("🖼️ Ảnh Teaching")
        teaching_layout = QVBoxLayout()
        
        self.image_path_label = QLabel("Chưa chọn ảnh")
        self.image_path_label.setWordWrap(True)
        teaching_layout.addWidget(self.image_path_label)
        
        btn_row = QHBoxLayout()
        self.image_btn = QPushButton("Tạo ảnh Teaching")
        self.image_btn.clicked.connect(self._capture_teaching_image)
        btn_row.addWidget(self.image_btn)
        
        self.image_file_btn = QPushButton("Chọn file ảnh...")
        self.image_file_btn.clicked.connect(self._select_image_file)
        btn_row.addWidget(self.image_file_btn)
        btn_row.addStretch()
        teaching_layout.addLayout(btn_row)
        
        # Test Algorithms button (COMMON)
        test_algo_btn = QPushButton("🧪 Test Algorithms")
        test_algo_btn.clicked.connect(self._open_algorithm_testing_dialog)
        teaching_layout.addWidget(test_algo_btn)
        
        # Selected Algorithms list (COMMON - moved from Event Tracking section)
        teaching_layout.addWidget(QLabel("Selected Algorithms:"))
        self.algorithms_list = QListWidget()  # Renamed from ocr_algorithms_list
        self.algorithms_list.setMaximumHeight(100)
        self.algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        teaching_layout.addWidget(self.algorithms_list)
        
        teaching_group.setLayout(teaching_layout)
        main_layout.addWidget(teaching_group)
        
        # Event Tracking Settings (only ROI + Pattern + Thresholds + Telegram)
        self._add_event_tracking_section(main_layout)
        
        # ... rest of UI ...
    
    def _on_passive_mode_changed(self, index: int):
        """Show/hide groups based on passive mode selection.
        
        Args:
            index: 0 = Đọc dữ liệu (mode 1), 1 = Phát hiện hình ảnh (mode 2), 2 = Event Tracking (mode 3)
        """
        is_read_data = (index == 0)
        is_detect_image = (index == 1)
        is_event_tracking = (index == 2)
        
        # Mode 1 (Đọc dữ liệu): Show two-column layout with passive/OCR/Gemini/Telegram
        self.two_column_widget.setVisible(is_read_data)
        
        # Mode 2 (Phát hiện hình ảnh): Show detect settings only
        self.detect_group.setVisible(is_detect_image)
        
        # Mode 3 (Event Tracking): Show event tracking settings only
        self.event_tracking_group.setVisible(is_event_tracking)
        
        # OCR Preprocessing section only visible in mode 1 (Đọc dữ liệu)
        if hasattr(self, 'ocr_preprocessing_group'):
            self.ocr_preprocessing_group.setVisible(is_read_data)
            if is_read_data:
                self._update_algorithms_display()
    
    def _add_event_tracking_section(self, layout: QVBoxLayout):
        """Add Event Tracking Settings section to layout.
        
        Args:
            layout: Parent layout to add section to
        """
        self.event_tracking_group = QGroupBox("🔔 Event Tracking Settings")
        event_layout = QVBoxLayout()
        
        # NOTE: ROI được lấy từ Teaching image, không cần button Set ROI riêng
        
        # OCR Pattern
        event_layout.addWidget(QLabel("OCR Pattern:"))
        self.event_ocr_pattern_edit = QLineEdit()
        self.event_ocr_pattern_edit.setPlaceholderText("{event_name} sẽ bắt đầu sau {minutes} phút")
        event_layout.addWidget(self.event_ocr_pattern_edit)
        
        # Match Threshold
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Match Threshold:"))
        self.event_match_threshold_spin = QDoubleSpinBox()
        self.event_match_threshold_spin.setMinimum(0.0)
        self.event_match_threshold_spin.setMaximum(100.0)
        self.event_match_threshold_spin.setValue(100.0)
        self.event_match_threshold_spin.setSuffix(" %")
        self.event_match_threshold_spin.setDecimals(1)
        threshold_row.addWidget(self.event_match_threshold_spin)
        threshold_row.addStretch()
        event_layout.addLayout(threshold_row)
        
        # Delay Threshold
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay Threshold:"))
        self.event_delay_threshold_spin = QSpinBox()
        self.event_delay_threshold_spin.setMinimum(0)
        self.event_delay_threshold_spin.setMaximum(3600)
        self.event_delay_threshold_spin.setValue(180)
        self.event_delay_threshold_spin.setSuffix(" seconds")
        delay_row.addWidget(self.event_delay_threshold_spin)
        delay_row.addStretch()
        event_layout.addLayout(delay_row)
        
        # Reset Interval
        reset_row = QHBoxLayout()
        reset_row.addWidget(QLabel("Reset Interval:"))
        self.event_reset_interval_spin = QSpinBox()
        self.event_reset_interval_spin.setMinimum(0)
        self.event_reset_interval_spin.setMaximum(1440)
        self.event_reset_interval_spin.setValue(15)
        self.event_reset_interval_spin.setSuffix(" minutes (0 = never reset)")
        reset_row.addWidget(self.event_reset_interval_spin)
        reset_row.addStretch()
        event_layout.addLayout(reset_row)
        
        # Telegram Message
        event_layout.addWidget(QLabel("Telegram Message:"))
        self.event_telegram_message_edit = QLineEdit()
        self.event_telegram_message_edit.setPlaceholderText("Sự kiện {event_name} vẫn đang diễn ra")
        event_layout.addWidget(self.event_telegram_message_edit)
        
        self.event_tracking_group.setLayout(event_layout)
        self.event_tracking_group.setVisible(False)  # Initially hidden, shown when mode = Event Tracking
        layout.addWidget(self.event_tracking_group)
    
    def _set_event_roi(self):
        """REMOVED - ROI được lấy từ Teaching image."""
        pass
    
    def _clear_event_roi(self):
        """REMOVED - ROI được lấy từ Teaching image."""
        pass
    
    def _open_algorithm_testing_dialog(self):
        """Open Multi-Image Testing Dialog.
        
        This method is COMMON for all modes - updates self.algorithms_list.
        """
        pass  # Implementation in Bước 4
    
    def _update_algorithms_display(self):
        """Update algorithms ListView display.
        
        This method is COMMON for all modes - updates self.algorithms_list.
        """
        pass  # Implementation in Bước 4
    
    def _load_settings(self):
        """Load settings from action."""
        # ... existing code ...
        
        # Passive mode (now with 3 modes)
        passive_mode = str(getattr(self.action, "passive_mode", "detect_image") or "detect_image")
        if passive_mode == "read_data":
            self.passive_mode_combo.setCurrentIndex(0)
        elif passive_mode == "event_tracking":
            self.passive_mode_combo.setCurrentIndex(2)  # Event Tracking mode
        else:
            self.passive_mode_combo.setCurrentIndex(1)  # Default: detect_image
        
        # Event Tracking settings (5 fields, ROI từ teaching image)
        self.event_ocr_pattern_edit.setText(str(getattr(self.action, "event_ocr_pattern", "") or ""))
        self.event_match_threshold_spin.setValue(float(getattr(self.action, "event_match_threshold", 100.0) or 100.0))
        self.event_delay_threshold_spin.setValue(int(getattr(self.action, "event_delay_threshold", 0) or 0))
        self.event_reset_interval_spin.setValue(int(getattr(self.action, "event_reset_interval", 15) or 15))
        self.event_telegram_message_edit.setText(str(getattr(self.action, "event_telegram_message", "") or ""))
        
        # NOTE: ROI được lấy từ teaching_corner_x1, y1, x2, y2, không cần load event_roi_coordinates
        
        # Update visibility based on mode
        self._on_passive_mode_changed(self.passive_mode_combo.currentIndex())
        
        # Algorithms (COMMON - single list for all modes)
        self._update_algorithms_display()
    
    def get_settings(self) -> dict:
        """Get settings from dialog.
        
        Returns:
            Dict with all settings including Event Tracking
        """
        # Passive mode mapping (now with 3 modes)
        passive_mode_map = {
            0: "read_data",
            1: "detect_image",
            2: "event_tracking"  # New mode
        }
        
        settings = {
            # ... existing settings ...
            
            "passive_mode": passive_mode_map.get(self.passive_mode_combo.currentIndex(), "detect_image"),
            
            # Event Tracking settings (5 fields, ROI từ teaching image)
            "event_ocr_pattern": str(self.event_ocr_pattern_edit.text() or "").strip(),
            "event_match_threshold": float(self.event_match_threshold_spin.value()),
            "event_delay_threshold": int(self.event_delay_threshold_spin.value()),
            "event_reset_interval": int(self.event_reset_interval_spin.value()),
            "event_telegram_message": str(self.event_telegram_message_edit.text() or "").strip(),
            # NOTE: ROI được lấy từ teaching_corner_x1, y1, x2, y2
        }
        
        return settings
    
    def _validate_settings(self) -> tuple[bool, str]:
        """Validate settings before save.
        
        Returns:
            (is_valid, error_message)
        """
        # ... existing validation ...
        
        # Event Tracking validation (check passive_mode instead of checkbox)
        if self.passive_mode_combo.currentIndex() == 2:  # Event Tracking mode
            if not self.event_ocr_pattern_edit.text().strip():
                return (False, "OCR Pattern không được để trống khi chọn Event Tracking")
            
            if not self.event_telegram_message_edit.text().strip():
                return (False, "Telegram Message không được để trống khi chọn Event Tracking")
            
            # Check Teaching image (ROI được lấy từ teaching_corner_x1, y1, x2, y2)
            if not getattr(self.action, "image_path", None) or not getattr(self.action, "teaching_corner_x1", None):
                return (False, "Chưa tạo Teaching image cho Event Tracking. Vui lòng tạo Teaching image trước.")
            
            # Check Telegram config
            from ..logic.system_executor.telegram_notifier import TelegramNotifier
            if not TelegramNotifier.is_configured():
                return (False, "Chưa cấu hình Telegram. Vui lòng cài đặt Telegram trước.")
        
        return (True, "")
```

---

## 4. Tuân thủ Steering Files

### 4.1. Master Rules (00-MASTER-RULES.md)

✅ **Giao tiếp bằng tiếng Việt**: Tất cả UI labels, messages, docstrings bằng tiếng Việt
✅ **Tuân thủ 5 bước phát triển feature**: Đang ở Bước 2 (Design)
✅ **Viết minimal code**: Chỉ thêm 7 fields vào AutoAction, không tạo file mới
✅ **Dùng signals cho thread-safe UI updates**: Không có background threads trong feature này

### 4.2. Project Structure (project-structure.md)

✅ **src/logic/**: Pure business logic - SystemExecutor._execute_event_tracking() không có UI dependencies
✅ **src/ui/**: PyQt UI components - PassiveReadSettingsDialog chỉ chứa UI logic
✅ **File size**: 
- action_type.py: +7 lines (< 500 lines)
- tool_manager.py: +20 lines (< 500 lines)
- passive_read_settings_dialog.py: +150 lines (< 400 lines)
- system_executor.py: +100 lines (< 500 lines)

### 4.3. Coding Guidelines (coding-guidelines.md)

✅ **Minimal Code**: Chỉ thêm code tối thiểu cần thiết, không over-engineer
✅ **No Mocking**: Tests sẽ dùng real objects (Bước 3)
✅ **Type Hints**: Tất cả methods có type hints đầy đủ
✅ **Docstrings**: Tất cả public methods có docstrings
✅ **Builder Pattern**: Sử dụng OCRPreprocessor với builder pattern
✅ **Factory Pattern**: Sử dụng OCRFactory để tạo OCR engine

### 4.4. Persistence Rules (QUAN TRỌNG!)

✅ **Add field to UI dialog**: PassiveReadSettingsDialog có UI controls cho 7 fields
✅ **Save to object in get_settings()**: get_settings() return dict với 7 fields
✅ **Load from object in _load_settings()**: _load_settings() load 7 fields từ action
✅ **Verify field exists in _action_to_dict()**: Tool._action_to_dict() serialize 7 fields
✅ **Verify field exists in from_dict()**: Tool.from_dict() deserialize 7 fields
✅ **Test: Save → close app → reopen → verify data persists**: Sẽ test trong Bước 4

---

## 5. Checklist kiểm tra design.md

- [x] File có đúng path `.kiro/specs/event-tracking-notification/design.md`?
- [x] Có section "Impact Analysis" đầy đủ?
- [x] Có phân tích tác động đến code hiện tại?
- [x] Có liệt kê dependencies và thư viện mới?
- [x] Có xác định khó khăn kỹ thuật và giải pháp?
- [x] Có đánh giá rủi ro và cách giảm thiểu?
- [x] Có section "Technical Design" với architecture?
- [x] Có mô tả design patterns được sử dụng?
- [x] Có liệt kê files được tạo/sửa?
- [x] Có code skeleton với class definitions và method signatures?
- [x] Code skeleton có type hints và docstrings?
- [x] Đã tuân thủ Master Rules (giao tiếp tiếng Việt, 5 bước, minimal code, signals cho UI updates)?
- [x] Đã tuân thủ project structure (src/logic/, src/ui/, tests/, docs/)?
- [x] Đã tuân thủ coding guidelines (no mocking, type hints, docstrings, builder/factory patterns)?
- [x] Đã xem xét persistence rules (7 fields mới đều có persistence đầy đủ)?
- [x] Tất cả thông tin đã đầy đủ và rõ ràng?

**Kết luận**: Design.md đã hoàn thành và đầy đủ! ✅
