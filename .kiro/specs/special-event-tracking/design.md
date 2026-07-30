# Design: Special Event Tracking Mode

---

## 1. IMPACT ANALYSIS

### Files bị ảnh hưởng

| File                                                        | Loại thay đổi | Mô tả                                                              |
|-------------------------------------------------------------|---------------|--------------------------------------------------------------------|
| `src/ui/passive_read_settings_dialog.py`                    | Modify        | Thêm mode "Special Event Tracking" vào dropdown, thêm UI section  |
| `src/logic/action_type.py`                                  | Modify        | Thêm fields mới cho special event tracking vào `AutoAction`        |
| `src/logic/tool_manager.py`                                 | Modify        | Thêm fields vào `_action_to_dict()` và `from_dict()`              |
| `src/logic/system_executor/system_executor.py`              | Modify        | Routing guard + setup/teardown special event subscriptions         |
| `src/logic/system_executor/imperial_guardian_handler.py`    | New           | Handler logic cho Imperial Guardian event                          |
| `src/logic/system_executor/golden_invasion_handler.py`      | New           | Handler logic cho Golden Invasion event                            |
| `src/logic/system_executor/monster_invasion_handler.py`     | New           | Fan-out handler cho Monster Invasion (Golden Invasion + WW+RD)     |
| `src/logic/system_executor/golden_invasion_sub_handler.py`  | New           | Sub-handler Golden Invasion trong Monster Invasion                 |
| `src/logic/system_executor/white_wizard_red_dragon_handler.py` | New        | Sub-handler White Wizard + Red Dragon                              |
| `src/logic/system_executor/screen_scan_service.py`          | No change     | Đã hỗ trợ subscribe/unsubscribe theo `action_id` string           |

### Dependencies

- `ScreenScanService`: đã có `subscribe(OCRSubscription)` và `unsubscribe(action_id: str)` — dùng được ngay
- `OCRSubscription`: nhận `action_id` string làm key — sẽ dùng `special_event:{action_id}:imperial_guardian`
- `TelegramNotifier`: đã có trong `SystemExecutor` — dùng lại
- Qt signals: dùng `engine.signals.log.emit()` cho thread-safe UI updates
- `rapidfuzz`: đã cài sẵn trong project (dùng trong `event_tracking_helper.py`), không cần thêm dependency mới. `rapidfuzz` là **optional** — nếu không có, handler fallback sang substring matching (`pattern in text`). Fuzzy matching sẽ không hoạt động nhưng không crash.

### Technical Risks

- `ScreenScanService.unsubscribe()` dùng `action_id` làm key — subscription identity `special_event:{action_id}:imperial_guardian` là string hợp lệ, không conflict
- Imperial Guardian handler chạy trong scan thread → mọi UI update phải qua Qt signals
- Nếu `rapidfuzz` chưa được cài, import sẽ fail → cần try/except fallback trong handler

---

## 2. ARCHITECTURE

### 2.1. Tổng quan

```
PassiveReadSettingsDialog
  └── Mode: Special Event Tracking (index 3)
        └── Special Events section (framework-level)
              └── Per-event collapsible section (shared pattern for all events):
                    ├── QCheckBox enable/disable
                    ├── QSpinBox no_player_alert_delay  <- shared framework control
                    ├── QComboBox ocr_engine            <- shared framework control
                    ├── QSpinBox match_threshold        <- shared framework control
                    ├── QPushButton Select Teaching Image (ROI)
                    ├── QPushButton Test Algorithms     <- shared framework control
                    └── QListWidget selected algorithms <- shared framework control
              └── [Currently only Imperial Guardian is implemented]

SystemExecutor._run_passive_read()
  └── mode == "special_event_tracking"
        └── _run_passive_read_via_scan_service()
              └── _setup_special_event_subscriptions()
                    └── ImperialGuardianHandler(threshold, delay) -> subscribe -> ScreenScanService
              └── [keep alive until stop/cancel]
              └── finally: _teardown_special_event_subscriptions()
```

> Cac controls no_player_alert_delay, ocr_engine, match_threshold, ocr_algorithms la shared framework controls - moi event deu co bo controls nay. Hien tai chi implement cho Imperial Guardian, nhung pattern nay se duoc tai su dung cho cac event tuong lai.

### 2.2. Module placement

- `src/ui/` → UI changes (dialog)
- `src/logic/` → action_type, tool_manager
- `src/logic/system_executor/` → imperial_guardian_handler.py (new), system_executor changes

---

## 3. CHI TIẾT THIẾT KẾ

### 3.1. `src/logic/action_type.py`

```python
# Thêm vào AutoAction

# Special Event Tracking – Imperial Guardian
imperial_guardian_enabled: bool = False
imperial_guardian_no_player_alert_delay: int = 10  # phút
imperial_guardian_teaching_corner_x1: int = 0
imperial_guardian_teaching_corner_y1: int = 0
imperial_guardian_teaching_corner_x2: int = 0
imperial_guardian_teaching_corner_y2: int = 0
imperial_guardian_ocr_engine: str = "auto"  # OCR engine: auto, winrt, tesseract, easyocr, vietocr
imperial_guardian_match_threshold: float = 70.0  # Ngưỡng fuzzy matching cả câu (0-100)
imperial_guardian_ocr_algorithms: list = []  # Preprocessing algorithms cho OCR ROI
```

### 3.2. `src/logic/tool_manager.py`

Các fields `imperial_guardian_*` được persist theo cùng pattern với `event_ocr_pattern` — setattr sau constructor trong `from_dict()`:

```python
# _action_to_dict() — thêm vào dict trả về
d["imperial_guardian_enabled"] = getattr(action, "imperial_guardian_enabled", False)
d["imperial_guardian_no_player_alert_delay"] = getattr(action, "imperial_guardian_no_player_alert_delay", 10)
d["imperial_guardian_teaching_corner_x1"] = getattr(action, "imperial_guardian_teaching_corner_x1", 0)
d["imperial_guardian_teaching_corner_y1"] = getattr(action, "imperial_guardian_teaching_corner_y1", 0)
d["imperial_guardian_teaching_corner_x2"] = getattr(action, "imperial_guardian_teaching_corner_x2", 0)
d["imperial_guardian_teaching_corner_y2"] = getattr(action, "imperial_guardian_teaching_corner_y2", 0)
d["imperial_guardian_ocr_engine"] = getattr(action, "imperial_guardian_ocr_engine", "auto")
d["imperial_guardian_match_threshold"] = getattr(action, "imperial_guardian_match_threshold", 70.0)
d["imperial_guardian_ocr_algorithms"] = getattr(action, "imperial_guardian_ocr_algorithms", [])

# from_dict() — setattr sau constructor (cùng pattern với event_ocr_pattern)
action.imperial_guardian_enabled = bool(a_data.get("imperial_guardian_enabled", False))
action.imperial_guardian_no_player_alert_delay = int(a_data.get("imperial_guardian_no_player_alert_delay", 10) or 10)
action.imperial_guardian_teaching_corner_x1 = int(a_data.get("imperial_guardian_teaching_corner_x1", 0) or 0)
action.imperial_guardian_teaching_corner_y1 = int(a_data.get("imperial_guardian_teaching_corner_y1", 0) or 0)
action.imperial_guardian_teaching_corner_x2 = int(a_data.get("imperial_guardian_teaching_corner_x2", 0) or 0)
action.imperial_guardian_teaching_corner_y2 = int(a_data.get("imperial_guardian_teaching_corner_y2", 0) or 0)
action.imperial_guardian_ocr_engine = str(a_data.get("imperial_guardian_ocr_engine", "auto") or "auto")
action.imperial_guardian_match_threshold = float(a_data.get("imperial_guardian_match_threshold", 70.0) or 70.0)
action.imperial_guardian_ocr_algorithms = list(a_data.get("imperial_guardian_ocr_algorithms", []) or [])
```

### 3.3. `src/ui/passive_read_settings_dialog.py`

**Dropdown:**
```python
self.passive_mode_combo.addItems([
    "Đọc dữ liệu",
    "Phát hiện hình ảnh",
    "Event Tracking",
    "Special Event Tracking",  # index 3
])
```

**Section Special Events (collapsible per event):**
```python
def _add_special_event_tracking_section(self, layout: QVBoxLayout) -> None:
    self.special_event_group = QGroupBox("🎯 Special Events")

    self.ig_checkbox = QCheckBox("Imperial Guardian")
    self.ig_checkbox.stateChanged.connect(self._on_ig_checkbox_changed)

    self.ig_settings_widget = QWidget()  # ẩn/hiện theo checkbox
    # - QSpinBox ig_delay_spin: range 1-120, default 10, suffix " phút"
    # - QPushButton ig_teaching_btn: "Tạo ảnh Teaching"
    # - QPushButton ig_teaching_file_btn: "Chọn file ảnh..."
    # - QLabel ig_teaching_label: hiển thị path ảnh

def _on_ig_checkbox_changed(self, state: int) -> None:
    self.ig_settings_widget.setVisible(bool(state))
```

**`_on_passive_mode_changed`:**
```python
is_special_event = (index == 3)
if hasattr(self, 'special_event_group'):
    self.special_event_group.setVisible(is_special_event)
```

**`get_settings()` / `_load_settings()`:**
```python
# get_settings
self.action.imperial_guardian_enabled = self.ig_checkbox.isChecked()
self.action.imperial_guardian_no_player_alert_delay = self.ig_delay_spin.value()
self.action.imperial_guardian_teaching_corner_x1 = ...  # từ teaching widget của IG
# ... y1, x2, y2
self.action.imperial_guardian_ocr_engine = ["auto","winrt","tesseract","easyocr","vietocr"][self.imperial_guardian_ocr_engine_combo.currentIndex()]
self.action.imperial_guardian_match_threshold = float(self.imperial_guardian_threshold_spin.value())
self.action.imperial_guardian_ocr_algorithms = getattr(self.action, "imperial_guardian_ocr_algorithms", [])

# _load_settings
self.ig_checkbox.setChecked(self.action.imperial_guardian_enabled)
self.ig_delay_spin.setValue(self.action.imperial_guardian_no_player_alert_delay)
self.imperial_guardian_ocr_engine_combo.setCurrentIndex(["auto","winrt","tesseract","easyocr","vietocr"].index(self.action.imperial_guardian_ocr_engine))
self.imperial_guardian_threshold_spin.setValue(int(self.action.imperial_guardian_match_threshold))
self.ig_settings_widget.setVisible(self.action.imperial_guardian_enabled)
# update algorithms list display
update_algorithms_display(self.imperial_guardian_algorithms_list, self.action.imperial_guardian_ocr_algorithms)
```

**Widgets mới trong Imperial Guardian section:**
```python
# SpinBox threshold
self.imperial_guardian_threshold_spin = QSpinBox()
self.imperial_guardian_threshold_spin.setRange(0, 100)
self.imperial_guardian_threshold_spin.setValue(70)
self.imperial_guardian_threshold_spin.setSuffix("%")

# Button Test Algorithms
test_algo_btn = QPushButton("🧪 Test Algorithms")
test_algo_btn.clicked.connect(self._open_imperial_guardian_algorithm_testing)

# QListWidget algorithms (read-only display)
self.imperial_guardian_algorithms_list = QListWidget()
self.imperial_guardian_algorithms_list.setMaximumHeight(80)
self.imperial_guardian_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

def _open_imperial_guardian_algorithm_testing(self) -> None:
    """Mo MultiImageAlgorithmTestingDialog voi ROI cua Imperial Guardian."""
    from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    dialog = MultiImageAlgorithmTestingDialog(
        hwnd=self.target_window_hwnd,
        action=self.action,
        parent=self,
    )
    if dialog.exec():
        # Luu truc tiep vao imperial_guardian_ocr_algorithms, khong qua ocr_algorithms generic
        self.action.imperial_guardian_ocr_algorithms = list(dialog.get_selected_algorithms() or [])
        update_algorithms_display(self.imperial_guardian_algorithms_list, self.action.imperial_guardian_ocr_algorithms)
```

### 3.4. `src/logic/system_executor/imperial_guardian_handler.py`

```python
"""Imperial Guardian Event Handler."""

import threading
import time
import re
from typing import Callable, Optional

try:
    from rapidfuzz import fuzz as _fuzz
    def _fuzzy_match(pattern: str, text: str, threshold: float) -> bool:
        return _fuzz.partial_ratio(pattern, text) >= threshold
except ImportError:
    def _fuzzy_match(pattern: str, text: str, threshold: float) -> bool:
        return pattern in text  # fallback


REOPEN_RULES: list[tuple[int, int, int]] = [
    (0, 7, 60), (7, 12, 45), (12, 18, 30), (18, 20, 20), (20, 24, 15),
]

# Patterns phai dung tieng Viet co dau day du (Unicode) - xem imperial-guardian-event-tracker.md
# OCR text duoc lowercase truoc khi match voi rapidfuzz.partial_ratio
# Patterns ngan de tang kha nang match khi OCR bi cat bot
PATTERNS_OPEN: list[str] = [
    "sự kiện imperial guardian đã bắt đầu",
]
PATTERNS_COUNTDOWN: list[str] = [
    "sự kiện imperial guardian sẽ bắt đầu sau",
]


class ImperialGuardianHandler:
    """Handles Imperial Guardian event tracking logic.

    State machine: WAITING -> OPEN -> CLOSED -> OPEN (cycle)
    WAITING: initial state only
    OPEN: event active, timer running for no-player alert
    CLOSED: event closed, waiting for next open
    """

    def __init__(
        self,
        action_id: str,
        no_player_alert_delay: int,
        match_threshold: float,
        telegram_notifier: object,
        log_signal_emit: Callable[[str], None],
    ) -> None:
        self._action_id = action_id
        self._delay_minutes = no_player_alert_delay
        self._threshold = match_threshold
        self._telegram = telegram_notifier
        self._log = log_signal_emit
        self._state: str = "WAITING"
        self._open_time: Optional[float] = None
        self._no_player_alert_sent: bool = False
        self._cached_text: Optional[str] = None
        self._lock = threading.Lock()

    def on_ocr_text(self, text: str) -> None:
        """OCR callback. Timer check runs BEFORE dedup."""
        if not text:
            return
        with self._lock:
            self._check_no_player_alert()  # always run, independent of dedup
            normalized = text.lower().strip()
            if normalized == self._cached_text:
                return  # dedup: skip pattern matching only
            self._cached_text = normalized
            self._process(normalized)

    def _check_no_player_alert(self) -> None:
        if (self._state == "OPEN"
                and not self._no_player_alert_sent
                and self._open_time is not None
                and (time.time() - self._open_time) > self._delay_minutes * 60):
            self._no_player_alert_sent = True
            self._send_telegram(
                f"Sự kiện Imperial Guardian đang không có người tham gia sau {self._delay_minutes} phút"
            )

    def _process(self, text: str) -> None:
        if self._match(text, PATTERNS_OPEN):
            if self._state != "OPEN":
                self._state = "OPEN"
                self._open_time = time.time()
                self._no_player_alert_sent = False
                self._send_telegram("Sự kiện Imperial Guardian đã bắt đầu")
            return
        if self._state == "OPEN" and self._match(text, PATTERNS_COUNTDOWN):
            x = self._extract_minutes(text)
            if x is not None and x >= self._get_reopen_time():
                self._state = "CLOSED"
                self._open_time = None
                self._send_telegram(f"Sự kiện Imperial Guardian đã đóng, mở sau {x} phút")

    def _match(self, text: str, patterns: list[str]) -> bool:
        return any(_fuzzy_match(p, text, self._threshold) for p in patterns)

    def _extract_minutes(self, text: str) -> Optional[int]:
        m = re.search(r'(\d+)\s*phút', text) or re.search(r'(\d+)\s*phut', text)
        return int(m.group(1)) if m else None

    def _get_reopen_time(self) -> int:
        hour = time.localtime().tm_hour
        for start, end, minutes in REOPEN_RULES:
            if start <= hour < end:
                return minutes
        return 15

    def _send_telegram(self, message: str) -> None:
        try:
            if self._telegram:
                self._telegram.send_simple(message)
        except Exception as e:
            self._log(f"[Imperial Guardian] Telegram error: {e}")
```

### 3.5. `src/logic/system_executor/system_executor.py` — Routing + Lifecycle

**F-001 fix: Routing guard trong `_run_passive_read()` (hoặc `execute_passive_read_action()`):**

```python
mode = getattr(action, "passive_mode", "detect_image")

if mode in ("read_data", "event_tracking", "special_event_tracking"):
    self._run_passive_read_via_scan_service(action, timeout)
else:
    # existing detect_image path
    ...
```

**Trong `_run_passive_read_via_scan_service(self, action: AutoAction, timeout: float | None)`:**

Giữ nguyên signature hiện tại, chỉ thêm branch cho `special_event_tracking`:

```python
def _run_passive_read_via_scan_service(self, action: AutoAction, timeout: float | None = None) -> None:
    mode = getattr(action, "passive_mode", "detect_image")

    if mode == "special_event_tracking":
        hwnd = self.target_window_hwnd  # dùng self.target_window_hwnd như các mode khác
        self._setup_special_event_subscriptions(action, hwnd)
        try:
            # Keep alive dùng pattern hiện tại của project
            while True:
                if self.engine and (not self.engine.is_running or self.engine.should_stop_completely):
                    break
                if getattr(self.engine, "cancel_cycle_requested", False):
                    break
                time.sleep(1.0)
        finally:
            self._teardown_special_event_subscriptions(action)

    elif mode == "event_tracking":
        # existing logic unchanged
        ...
    elif mode == "read_data":
        # existing logic unchanged
        ...
```

**Setup/Teardown — dùng `id(action)` thay vì `action.id` (F-002 fix):**

```python
def _setup_special_event_subscriptions(self, action: AutoAction, hwnd: int) -> None:
    """Subscribe enabled special events to ScreenScanService."""
    from .imperial_guardian_handler import ImperialGuardianHandler
    from .screen_scan_service import ScreenScanService, OCRSubscription

    service = ScreenScanService.get_instance()
    # Dùng id(action) + name như pattern hiện tại, không dùng action.id
    action_key = f"{id(action)}_{getattr(action, 'name', 'unknown')}"

    if getattr(action, "imperial_guardian_enabled", False):
        x1 = action.imperial_guardian_teaching_corner_x1
        y1 = action.imperial_guardian_teaching_corner_y1
        x2 = action.imperial_guardian_teaching_corner_x2
        y2 = action.imperial_guardian_teaching_corner_y2

        if x2 <= x1 or y2 <= y1:
            self._ui_log("[Special Event] Imperial Guardian: ROI chưa cấu hình, bỏ qua")
            return

        roi = (x1, y1, x2 - x1, y2 - y1)
        handler = ImperialGuardianHandler(
            action_id=action_key,  # dùng action_key làm action_id
            no_player_alert_delay=action.imperial_guardian_no_player_alert_delay,
            match_threshold=getattr(action, "imperial_guardian_match_threshold", 70.0),
            telegram_notifier=self.telegram_notifier,
            log_signal_emit=self._ui_log,
        )
        sub_id = f"special_event:{action_key}:imperial_guardian"
        sub = OCRSubscription(
            action_id=sub_id,
            hwnd=hwnd,
            roi=roi,
            ocr_engine=getattr(action, "imperial_guardian_ocr_engine", "auto"),
            ocr_algorithms=getattr(action, "imperial_guardian_ocr_algorithms", []),
            callback=handler.on_ocr_text,
        )
        service.subscribe(sub)
        self._ui_log("[Special Event] Imperial Guardian: đã subscribe")

def _teardown_special_event_subscriptions(self, action: AutoAction) -> None:
    """Unsubscribe all special events. Called in finally block on stop/cancel."""
    from .screen_scan_service import ScreenScanService
    action_key = f"{id(action)}_{getattr(action, 'name', 'unknown')}"
    ScreenScanService.get_instance().unsubscribe(f"special_event:{action_key}:imperial_guardian")
    self._ui_log("[Special Event] Imperial Guardian: đã unsubscribe")
```

---

## 4. SUBSCRIPTION LIFECYCLE

| Thời điểm                                    | Hành động                                                                 |
|----------------------------------------------|---------------------------------------------------------------------------|
| Action start, event enabled, ROI hợp lệ      | `_setup_special_event_subscriptions()` → subscribe                        |
| Action start, event disabled hoặc ROI invalid | Không subscribe, log cảnh báo                                             |
| Action stop/cancel (bình thường hoặc lỗi)    | `finally: _teardown_special_event_subscriptions()` → unsubscribe          |
| User lưu settings khi action đang chạy       | PassiveReader nhận settings mới → teardown → setup lại với settings mới   |
| Event bị untick khi action đang chạy         | Sau khi Lưu → unsubscribe `special_event:{action_id}:imperial_guardian`   |

---

## 5. THREAD SAFETY

```python
# ĐÚNG: log_signal_emit là Qt signal emit → QueuedConnection → UI thread
self._log = engine.signals.log.emit

# SAI: gọi trực tiếp QWidget từ scan thread
self.some_label.setText(...)  # KHÔNG làm thế này
```

---

## 6. PERSISTENCE FLOW

```
Dialog.accept()
  → get_settings() → action.imperial_guardian_* = widget values
  → tool_manager._action_to_dict() → JSON

App restart
  → tool_manager.from_dict() → action.imperial_guardian_* = JSON values (default nếu thiếu)
  → Dialog._load_settings() → widget values = action.*
```

---

## 7. BACKWARD COMPATIBILITY

- Mode `event_tracking` (index 2) giữ nguyên, không bị ảnh hưởng
- `from_dict()` dùng `d.get(..., default)` → JSON cũ không có fields mới vẫn load được
- `ScreenScanService` không thay đổi API
- `rapidfuzz` fallback đảm bảo không crash nếu chưa cài
