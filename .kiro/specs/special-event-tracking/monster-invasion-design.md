# Design: Monster Invasion Event Tracker

---

## 1. IMPACT ANALYSIS

### Files bi anh huong

| File                                                              | Loai thay doi | Mo ta                                                                                    |
|-------------------------------------------------------------------|---------------|------------------------------------------------------------------------------------------|
| `src/logic/action_type.py`                                        | Modify        | Them `monster_invasion_*` fields, giu `golden_invasion_*` cho backward compat           |
| `src/logic/tool_manager.py`                                       | Modify        | Them `monster_invasion_*` vao `_action_to_dict()` va `from_dict()`                      |
| `src/logic/system_executor/system_executor.py`                    | Modify        | Them Monster Invasion vao `_setup_special_event_subscriptions()`                         |
| `src/logic/system_executor/monster_invasion_handler.py`           | New           | Handler cha fan-out OCR text den sub-handlers                                            |
| `src/logic/system_executor/golden_invasion_sub_handler.py`        | New           | Sub-handler Golden Invasion (tach logic tu golden_invasion_handler.py)                   |
| `src/logic/system_executor/white_wizard_red_dragon_handler.py`    | New           | Sub-handler White Wizard + Red Dragon                                                    |
| `src/logic/system_executor/golden_invasion_handler.py`            | Keep          | Giu nguyen cho backward compat (Golden Invasion standalone)                              |
| `src/ui/passive_read_settings_dialog.py`                          | Modify        | Them Monster Invasion section voi shared ROI + 2 sub-event checkboxes                   |
| `src/ui/action_config_dialog.py`                                  | Modify        | Them `monster_invasion_*` fields vao READ_PASSIVE save block                            |

### Dependencies

- `ScreenScanService`: 2 subscriptions (channel + notify) dung chung cho ca 2 sub-events
- `normalize_ocr_text`: tu `event_tracking_helper.py` — dung trong ca 2 sub-handlers
- `TelegramNotifier`: dung lai trong ca 2 sub-handlers
- Qt signals: log qua `log_signal_emit` callback

### Technical Risks

- Monster Invasion dung chung 2 subscriptions — neu 1 sub-event throw exception, sub-event kia van phai tiep tuc → can try/except trong fan-out
- Backward compat: `golden_invasion_*` fields cu van con trong JSON → `from_dict()` phai doc duoc ca 2 format
- `pair_group_id` trong OCRSubscription hien tai chi dung cho Golden Invasion → Monster Invasion dung `mi:{handler_key}` lam group_id

---

## 2. ARCHITECTURE

### 2.1. Tong quan

```
PassiveReadSettingsDialog
  └── Mode: Special Event Tracking
        └── Special Events section
              ├── Imperial Guardian (existing, unchanged)
              └── Monster Invasion (new)
                    ├── QCheckBox enable/disable
                    ├── Vung 1: Channel (shared ROI + OCR engine + algorithms)
                    ├── Vung 2: Thong bao (shared ROI + OCR engine + algorithms)
                    ├── Match threshold (shared)
                    └── Sub-events:
                          ├── QCheckBox Golden Invasion
                          │     └── QRadioButton server_time (00:40 / 01:30)
                          └── QCheckBox White Wizard + Red Dragon

SystemExecutor._setup_special_event_subscriptions()
  └── Monster Invasion enabled + ROI valid
        └── MonsterInvasionHandler(sub_handlers=[...])
              ├── Subscribe Vung 1 → on_channel_text (fan-out)
              └── Subscribe Vung 2 → on_notify_text (fan-out)
                    ├── GoldenInvasionSubHandler (if enabled)
                    └── WhiteWizardRedDragonHandler (if enabled)
```

### 2.2. Module placement

- `src/logic/system_executor/` → monster_invasion_handler.py, golden_invasion_sub_handler.py, white_wizard_red_dragon_handler.py
- `src/ui/` → passive_read_settings_dialog.py, action_config_dialog.py
- `src/logic/` → action_type.py, tool_manager.py

---

## 3. CHI TIET THIET KE

### 3.1. `src/logic/action_type.py`

```python
# Them sau golden_invasion_* fields

# Monster Invasion Event Tracking (shared ROI/engine/algorithms for sub-events)
monster_invasion_enabled: bool = False
monster_invasion_channel_roi_x1: int = 0
monster_invasion_channel_roi_y1: int = 0
monster_invasion_channel_roi_x2: int = 0
monster_invasion_channel_roi_y2: int = 0
monster_invasion_channel_ocr_engine: str = "auto"
monster_invasion_channel_ocr_algorithms: list = None
monster_invasion_channel_teaching_image_path: str = ""
monster_invasion_notify_roi_x1: int = 0
monster_invasion_notify_roi_y1: int = 0
monster_invasion_notify_roi_x2: int = 0
monster_invasion_notify_roi_y2: int = 0
monster_invasion_notify_ocr_engine: str = "auto"
monster_invasion_notify_ocr_algorithms: list = None
monster_invasion_notify_teaching_image_path: str = ""
monster_invasion_match_threshold: float = 70.0
# Sub-event flags
monster_invasion_golden_invasion_enabled: bool = False
monster_invasion_golden_invasion_server_time: str = "01:30"
monster_invasion_white_wizard_red_dragon_enabled: bool = False
```

### 3.2. `src/logic/tool_manager.py`

```python
# _action_to_dict() — them sau golden_invasion fields
d["monster_invasion_enabled"] = getattr(action, "monster_invasion_enabled", False)
d["monster_invasion_channel_roi_x1"] = getattr(action, "monster_invasion_channel_roi_x1", 0)
d["monster_invasion_channel_roi_y1"] = getattr(action, "monster_invasion_channel_roi_y1", 0)
d["monster_invasion_channel_roi_x2"] = getattr(action, "monster_invasion_channel_roi_x2", 0)
d["monster_invasion_channel_roi_y2"] = getattr(action, "monster_invasion_channel_roi_y2", 0)
d["monster_invasion_channel_ocr_engine"] = getattr(action, "monster_invasion_channel_ocr_engine", "auto")
d["monster_invasion_channel_ocr_algorithms"] = getattr(action, "monster_invasion_channel_ocr_algorithms", [])
d["monster_invasion_channel_teaching_image_path"] = getattr(action, "monster_invasion_channel_teaching_image_path", "")
d["monster_invasion_notify_roi_x1"] = getattr(action, "monster_invasion_notify_roi_x1", 0)
d["monster_invasion_notify_roi_y1"] = getattr(action, "monster_invasion_notify_roi_y1", 0)
d["monster_invasion_notify_roi_x2"] = getattr(action, "monster_invasion_notify_roi_x2", 0)
d["monster_invasion_notify_roi_y2"] = getattr(action, "monster_invasion_notify_roi_y2", 0)
d["monster_invasion_notify_ocr_engine"] = getattr(action, "monster_invasion_notify_ocr_engine", "auto")
d["monster_invasion_notify_ocr_algorithms"] = getattr(action, "monster_invasion_notify_ocr_algorithms", [])
d["monster_invasion_notify_teaching_image_path"] = getattr(action, "monster_invasion_notify_teaching_image_path", "")
d["monster_invasion_match_threshold"] = getattr(action, "monster_invasion_match_threshold", 70.0)
d["monster_invasion_golden_invasion_enabled"] = getattr(action, "monster_invasion_golden_invasion_enabled", False)
d["monster_invasion_golden_invasion_server_time"] = getattr(action, "monster_invasion_golden_invasion_server_time", "01:30")
d["monster_invasion_white_wizard_red_dragon_enabled"] = getattr(action, "monster_invasion_white_wizard_red_dragon_enabled", False)

# from_dict() — setattr sau constructor
action.monster_invasion_enabled = bool(a_data.get("monster_invasion_enabled", False))
action.monster_invasion_channel_roi_x1 = int(a_data.get("monster_invasion_channel_roi_x1", 0) or 0)
# ... (tuong tu cho tat ca 19 fields)
action.monster_invasion_white_wizard_red_dragon_enabled = bool(a_data.get("monster_invasion_white_wizard_red_dragon_enabled", False))
```

### 3.3. `src/logic/system_executor/monster_invasion_handler.py`

```python
"""Monster Invasion event handler - fan-out OCR text to sub-handlers."""

import threading
from typing import Callable


class MonsterInvasionHandler:
    """Fan-out handler for Monster Invasion event.

    Receives OCR text from 2 shared subscriptions (channel + notify)
    and dispatches to enabled sub-handlers independently.
    Each sub-handler processes text and sends Telegram notifications.
    """

    def __init__(
        self,
        sub_handlers: list,
        log_signal_emit: Callable[[str], None],
    ) -> None:
        self._sub_handlers = sub_handlers
        self._log = log_signal_emit
        self._lock = threading.Lock()

    def on_channel_text(self, text: str) -> None:
        """Fan-out channel OCR text to all sub-handlers."""
        with self._lock:
            for handler in self._sub_handlers:
                try:
                    handler.on_channel_text(text)
                except Exception as e:
                    self._log(f"[Monster Invasion] Sub-handler error (channel): {e}")

    def on_notify_text(self, text: str) -> None:
        """Fan-out notify OCR text to all sub-handlers."""
        with self._lock:
            for handler in self._sub_handlers:
                try:
                    handler.on_notify_text(text)
                except Exception as e:
                    self._log(f"[Monster Invasion] Sub-handler error (notify): {e}")

    def reset(self) -> None:
        """Reset all sub-handlers."""
        for handler in self._sub_handlers:
            try:
                handler.reset()
            except Exception:
                pass
```

### 3.4. `src/logic/system_executor/golden_invasion_sub_handler.py`

Tach logic tu `golden_invasion_handler.py` thanh sub-handler dung trong Monster Invasion.
Interface giong het `GoldenInvasionHandler` hien tai:
- `on_channel_text(text)` — normalize + update channel_current + check event start
- `on_notify_text(text)` — normalize + parse kill + validate + send Telegram
- `reset()` — reset state

Khac biet duy nhat: khong tu subscribe, nhan text tu `MonsterInvasionHandler`.

### 3.5. `src/logic/system_executor/white_wizard_red_dragon_handler.py`

```python
"""White Wizard + Red Dragon event sub-handler."""

import re
import threading
import time
from typing import Callable, Optional
from datetime import datetime, timedelta

from .event_tracking_helper import normalize_ocr_text

EVENT_SCHEDULE = [
    "00:10", "01:10", "08:10", "09:10", "10:10", "11:10", "11:40",
    "12:10", "12:40", "13:10", "14:10", "15:10", "16:10", "17:10",
    "18:10", "19:10", "19:40", "20:10", "20:40", "21:10", "21:40",
    "22:10", "23:10",
]

RESET_MINUTES = 25

BOSS_DISPLAY = {
    "phu thuy trang": "Phu Thuy Trang",
    "rong do": "Rong Do",
}
BOSS_MAX_COUNT = {
    "phu thuy trang": 2,
    "rong do": 2,
}

PATTERN_KILL = r"(.+?)\s+da bi tieu diet boi\s+.+?\s+va dong doi tai\s+(.+)"


class WhiteWizardRedDragonHandler:
    """Sub-handler for White Wizard + Red Dragon event.

    State machine: WAITING -> ACTIVE (by schedule)
    No text cache - processes every OCR callback.
    Dedup by killed_map count (max 2 per boss type).
    Reset after 25 minutes.
    Telegram messages use Vietnamese with diacritics.
    """

    def __init__(
        self,
        match_threshold: float,
        telegram_notifier: object,
        log_signal_emit: Callable[[str], None],
    ) -> None:
        self._threshold = match_threshold
        self._telegram = telegram_notifier
        self._log = log_signal_emit
        self._state: str = "WAITING"
        self._channel_at_start: Optional[str] = None
        self._channel_current: Optional[str] = None
        self._killed_map: dict = {"phu thuy trang": 0, "rong do": 0}
        self._active_since: Optional[float] = None
        self._lock = threading.Lock()
        self._next_event_time: Optional[datetime] = None
        self._calculate_next_event_time()

    def _calculate_next_event_time(self) -> None:
        """Find next event slot from EVENT_SCHEDULE."""
        now = datetime.now()
        today_slots = []
        for slot in EVENT_SCHEDULE:
            h, m = map(int, slot.split(":"))
            dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if dt > now:
                today_slots.append(dt)
        if today_slots:
            self._next_event_time = min(today_slots)
        else:
            h, m = map(int, EVENT_SCHEDULE[0].split(":"))
            tomorrow = now + timedelta(days=1)
            self._next_event_time = tomorrow.replace(hour=h, minute=m, second=0, microsecond=0)
        self._log(f"[WW+RD] Next event: {self._next_event_time.strftime('%H:%M')}")

    def _check_event_start(self) -> None:
        if self._state == "WAITING" and self._next_event_time:
            if datetime.now() >= self._next_event_time:
                self._state = "ACTIVE"
                self._channel_at_start = self._channel_current
                self._killed_map = {"phu thuy trang": 0, "rong do": 0}
                self._active_since = time.time()
                self._log("[WW+RD] Event ACTIVE")
                self._calculate_next_event_time()

    def _check_reset_timer(self) -> None:
        if self._state == "ACTIVE" and self._active_since is not None:
            if time.time() - self._active_since >= RESET_MINUTES * 60:
                self._state = "WAITING"
                self._killed_map = {"phu thuy trang": 0, "rong do": 0}
                self._active_since = None
                self._log("[WW+RD] Reset after 25 minutes, back to WAITING")

    def _resolve_boss(self, extracted: str) -> Optional[str]:
        """Fuzzy match extracted boss name against known boss keys."""
        try:
            from rapidfuzz import fuzz as _rf
            best_score = -1.0
            best_key = None
            for key in BOSS_DISPLAY:
                score = float(_rf.partial_ratio(key, extracted))
                if score >= self._threshold and score > best_score:
                    best_score = score
                    best_key = key
            return best_key
        except ImportError:
            for key in BOSS_DISPLAY:
                if key in extracted:
                    return key
            return None

    def on_channel_text(self, text: str) -> None:
        """Update channel_current from Vung 1 OCR."""
        if not text:
            return
        with self._lock:
            self._channel_current = normalize_ocr_text(text)
            self._check_event_start()
            self._check_reset_timer()

    def on_notify_text(self, text: str) -> None:
        """Process kill notification from Vung 2 OCR. No text cache."""
        if not text or self._state != "ACTIVE":
            return
        with self._lock:
            self._check_reset_timer()
            if self._state != "ACTIVE":
                return
            if self._channel_at_start is None:
                return

            normalized = normalize_ocr_text(text)
            match = re.search(PATTERN_KILL, normalized)
            if not match:
                return

            extracted_boss = match.group(1).strip()
            map_name = match.group(2).strip()
            canonical_key = self._resolve_boss(extracted_boss)

            if canonical_key is None:
                return
            if self._killed_map[canonical_key] >= BOSS_MAX_COUNT[canonical_key]:
                return
            if self._channel_current != self._channel_at_start:
                self._log(f"[WW+RD] Channel changed, skip: {extracted_boss}")
                return

            self._killed_map[canonical_key] += 1
            remaining_white = BOSS_MAX_COUNT["phu thuy trang"] - self._killed_map["phu thuy trang"]
            remaining_red = BOSS_MAX_COUNT["rong do"] - self._killed_map["rong do"]
            total_killed = sum(self._killed_map.values())

            # Telegram message with Vietnamese diacritics
            display_names = {
                "phu thuy trang": "Phu Thuy Trang",
                "rong do": "Rong Do",
            }
            display_name = display_names[canonical_key]
            suffix = " - Da het boss!" if total_killed == 4 else ""
            message = (
                f"{display_name} da bi tieu diet tai {map_name} (SV {self._channel_current})\n"
                f"Con {remaining_white} Phu Thuy Trang va {remaining_red} Rong Do{suffix}"
            )
            self._send_telegram(message)

            if total_killed == 4:
                self._state = "WAITING"
                self._log("[WW+RD] All bosses killed, back to WAITING")

    def _send_telegram(self, message: str) -> None:
        try:
            if self._telegram:
                self._telegram.send_simple(message)
        except Exception as e:
            self._log(f"[WW+RD] Telegram error: {e}")

    def reset(self) -> None:
        self._state = "WAITING"
        self._channel_at_start = None
        self._channel_current = None
        self._killed_map = {"phu thuy trang": 0, "rong do": 0}
        self._active_since = None
```

### 3.6. `src/logic/system_executor/system_executor.py`

Them Monster Invasion block vao `_setup_special_event_subscriptions()` va `_teardown_special_event_subscriptions()`.
Xem Section 3.6 trong design doc.

### 3.7. `src/ui/passive_read_settings_dialog.py`

Them Monster Invasion section sau Golden Invasion section.
Widget names: `mi_checkbox`, `mi_settings_widget`, `mi_channel_roi_label`, `mi_channel_image_btn`,
`mi_channel_ocr_combo`, `mi_channel_test_algo_btn`, `mi_channel_algorithms_list`,
`mi_notify_roi_label`, `mi_notify_image_btn`, `mi_notify_ocr_combo`, `mi_notify_test_algo_btn`,
`mi_notify_algorithms_list`, `mi_threshold_spin`, `mi_gi_checkbox`, `mi_gi_time_0040`,
`mi_gi_time_0130`, `mi_ww_checkbox`.

---

## 4. SUBSCRIPTION LIFECYCLE

| Thoi diem                                    | Hanh dong                                                                 |
|----------------------------------------------|---------------------------------------------------------------------------|
| Action start, MI enabled, ca 2 ROI hop le   | Subscribe 2 subscriptions (channel + notify)                              |
| Action start, khong co sub-event nao enabled | Khong subscribe, log canh bao                                             |
| Action start, ROI invalid                    | Khong subscribe, log canh bao                                             |
| Action stop/cancel                           | finally: _teardown → unsubscribe ca 2, reset MI handler                   |

---

## 5. THREAD SAFETY

- `MonsterInvasionHandler` dung `threading.Lock()` trong fan-out
- Moi sub-handler co lock rieng
- Tat ca UI updates qua `log_signal_emit` (Qt signal emit)

---

## 6. PERSISTENCE FLOW

```
Dialog.accept()
  → get_settings() → action.monster_invasion_* = widget values
  → tool_manager._action_to_dict() → JSON

App restart
  → tool_manager.from_dict() → action.monster_invasion_* = JSON values
  → Dialog._load_settings() → widget values = action.*
```

---

## 7. BACKWARD COMPATIBILITY

- `golden_invasion_*` fields cu van giu trong `action_type.py` va `tool_manager.py`
- JSON cu co `golden_invasion_*` van load duoc (Golden Invasion standalone van hoat dong)
- Monster Invasion la feature moi, khong anh huong Golden Invasion standalone
- `from_dict()` dung `.get(..., default)` → JSON cu khong co `monster_invasion_*` van load duoc
