# Tasks: Special Event Tracking Mode

---

## Task 1: Viết unit tests cho ImperialGuardianHandler (test-first)

- [ ] 1.1 Tạo `tests/test_imperial_guardian_handler.py`
- [ ] 1.2 Test state machine: WAITING → OPEN khi nhận "đã bắt đầu"
- [ ] 1.3 Test state machine: OPEN → CLOSED khi nhận countdown X >= reopen_time
- [ ] 1.4 Test bỏ qua countdown X < reopen_time
- [ ] 1.5 Test no-player alert gửi sau Y phút khi vẫn OPEN
- [ ] 1.6 Test no-player alert không gửi nếu đã CLOSED trước Y phút
- [ ] 1.7 Test `_get_reopen_time()` trả đúng giá trị theo từng khung giờ
- [ ] 1.8 Test `_extract_minutes()` parse đúng số phút từ text

---

## Task 2: Viết unit tests cho persistence (test-first)

- [ ] 2.1 Tạo `tests/test_special_event_tracking_persistence.py`
- [ ] 2.2 Test round-trip: tạo action với 7 fields → `_action_to_dict()` → `from_dict()` → kiểm tra giá trị giữ nguyên (bao gồm `imperial_guardian_ocr_engine`)
- [ ] 2.3 Test backward compat: `from_dict()` với JSON cũ không có fields mới → default values đúng

---

## Task 3: Viết integration tests cho subscription lifecycle (test-first)

- [ ] 3.1 Tạo `tests/test_special_event_tracking_integration.py`
- [ ] 3.2 Test `_setup_special_event_subscriptions()` với ROI hợp lệ → subscription được tạo
- [ ] 3.3 Test `_setup_special_event_subscriptions()` với ROI invalid → không subscribe, log cảnh báo
- [ ] 3.4 Test `_teardown_special_event_subscriptions()` → subscription bị xóa

---

## Task 4: Tạo manual test plan

- [ ] 4.1 Tạo `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md` với các test case:
  - Chọn mode, tick/untick checkbox, lưu/load settings
  - Chạy action → subscribe; stop → unsubscribe
  - Persist: lưu → đóng app → mở lại → kiểm tra giá trị

---

## Task 5: Thêm fields vào AutoAction dataclass

- [ ] 5.1 Mở `src/logic/action_type.py`, thêm 7 fields vào `AutoAction`:
  - `imperial_guardian_enabled: bool = False`
  - `imperial_guardian_no_player_alert_delay: int = 10`
  - `imperial_guardian_teaching_corner_x1: int = 0`
  - `imperial_guardian_teaching_corner_y1: int = 0`
  - `imperial_guardian_teaching_corner_x2: int = 0`
  - `imperial_guardian_teaching_corner_y2: int = 0`
  - `imperial_guardian_ocr_engine: str = "auto"`

---

## Task 6: Cập nhật persistence trong tool_manager.py

- [ ] 6.1 Trong `_action_to_dict()`: thêm 7 fields dùng `getattr(action, ..., default)` (bao gồm `imperial_guardian_ocr_engine`)
- [ ] 6.2 Trong `from_dict()`: thêm setattr 7 fields sau constructor, dùng `bool/int/str` cast và `or default`
- [ ] 6.3 Chạy tests Task 2 → pass

---

## Task 7: Tạo ImperialGuardianHandler

- [ ] 7.1 Tạo file `src/logic/system_executor/imperial_guardian_handler.py`
- [ ] 7.2 Implement class `ImperialGuardianHandler` theo design
- [ ] 7.3 Chạy tests Task 1 → pass

---

## Task 8: Cập nhật SystemExecutor — routing và subscription lifecycle

- [ ] 8.1 Trong `_run_passive_read()`: thêm `"special_event_tracking"` vào routing guard
- [ ] 8.2 Trong `_run_passive_read_via_scan_service()`: thêm branch `mode == "special_event_tracking"`
- [ ] 8.3 Implement `_setup_special_event_subscriptions(self, action: AutoAction, hwnd: int) -> None`
- [ ] 8.4 Implement `_teardown_special_event_subscriptions(self, action: AutoAction) -> None`
- [ ] 8.5 Chạy tests Task 3 → pass

---

## Task 9: Cập nhật UI — PassiveReadSettingsDialog

- [ ] 9.1 Thêm item `"Special Event Tracking"` (index 3) vào `passive_mode_combo`
- [ ] 9.2 Implement `_add_special_event_tracking_section(self, layout: QVBoxLayout) -> None`
- [ ] 9.3 Implement `_on_ig_checkbox_changed(self, state: int) -> None`
- [ ] 9.4 Cập nhật `_on_passive_mode_changed()`: ẩn/hiện `special_event_group` khi index == 3
- [ ] 9.5 Cập nhật `get_settings()` và `_load_settings()` cho 7 fields mới (bao gồm `imperial_guardian_ocr_engine` với QComboBox)

---

## Task 10: Kiểm tra thủ công theo manual test plan

- [ ] 10.1 Thực hiện tất cả test cases trong `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`
