# Implementation Plan: User Input Detection

## Overview

Triển khai tính năng phát hiện thao tác người dùng khi tool đang chạy, cho phép tự động pause/stop tool.

## Tasks

- [x] 1. Cập nhật MouseController để đánh dấu events từ tool
  - [x] 1.1 Thêm constant TOOL_MARKER = 0xAUT0
  - [x] 1.2 Cập nhật _send_mouse_input() để set dwExtraInfo
  - [x] 1.3 Cập nhật click_with_optional_alt() để sử dụng marker
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Tạo UserInputDetector module
  - [x] 2.1 Tạo file src/logic/user_input_detector.py
  - [x] 2.2 Implement class UserInputDetector với signals
  - [x] 2.3 Implement start_listening() với pynput hooks
  - [x] 2.4 Implement stop_listening() và cleanup
  - [x] 2.5 Implement _is_in_target_window() check
  - [x] 2.6 Implement _on_mouse_event() với dwExtraInfo check
  - [x] 2.7 Implement _on_keyboard_event()
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 3. Checkpoint - Test UserInputDetector
  - Ensure hooks work correctly
  - Verify tool events are ignored
  - Verify user events are detected

- [x] 4. Cập nhật ToolRunner để xử lý user input
  - [x] 4.1 Thêm fields: user_input_mode, pause_duration, is_paused_by_user
  - [x] 4.2 Tạo UserInputDetector instance khi start
  - [x] 4.3 Connect signal user_input_detected
  - [x] 4.4 Implement _on_user_input_detected() handler
  - [x] 4.5 Implement pause logic với timer
  - [x] 4.6 Cleanup detector khi stop
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 5. Tạo UI cho Tool Settings
  - [x] 5.1 Thêm "User Input Mode" section vào ToolSettingsDialog
  - [x] 5.2 Thêm radio buttons: Ignore / Pause / Stop
  - [x] 5.3 Thêm SpinBox cho pause duration
  - [x] 5.4 Implement get_settings() để lấy values
  - [x] 5.5 Implement _load_settings() để load values
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 6. Cập nhật persistence (tool_manager.py)
  - [x] 6.1 Thêm user_input_mode vào Tool.__init__
  - [x] 6.2 Thêm pause_duration vào Tool.__init__
  - [x] 6.3 Thêm user_input_mode vào to_dict()
  - [x] 6.4 Thêm pause_duration vào to_dict()
  - [x] 6.5 Thêm user_input_mode vào from_dict()
  - [x] 6.6 Thêm pause_duration vào from_dict()
  - _Requirements: 3.5, 3.6_

- [x] 7. Integration: SystemExecutor + UserInputDetector
  - [x] 7.1 Thêm set_user_input_detector() vào SystemExecutor
  - [x] 7.2 Thêm _set_tool_acting() helper method
  - [x] 7.3 Wrap keyboard actions với _set_tool_acting()
  - [x] 7.4 Wrap mouse click actions với _set_tool_acting()
  - [x] 7.5 ToolRunner truyền detector vào executor

- [x] 8. Cập nhật UI status khi paused
  - [x] 8.1 Log message khi pause/resume
  - _Requirements: 4.4, 4.5, 4.6_

- [ ] 9. Final testing và documentation
  - [x] 9.1 Viết manual test plan
  - [ ] 9.2 Test edge cases
  - [ ] 9.3 Update docs nếu cần

## Notes

- pynput library đã được thêm vào requirements.txt
- Default mode là "ignore" (Vẫn chạy)
- Pause duration có thể cấu hình từ 1-300 giây, mặc định 5 giây
- Settings được lưu per-tool trong JSON
