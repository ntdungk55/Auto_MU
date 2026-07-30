# Implementation Plan: Event Tracking Notification

## Overview

Feature này thêm chế độ "Event Tracking" thứ 3 vào Passive Read Settings, cho phép tự động theo dõi thông báo sự kiện trên màn hình game, phát hiện thông báo mới khớp với pattern, và gửi cảnh báo qua Telegram sau khoảng thời gian delay. Mỗi thông báo khác nhau chỉ được gửi 1 lần trong khoảng Reset Interval để tránh spam.

Implementation approach:
1. Thêm 7 fields mới vào AutoAction dataclass
2. Update UI để hiển thị Event Tracking settings khi chọn mode 3
3. Implement logic xử lý Event Tracking trong SystemExecutor
4. Đảm bảo data persistence (serialization/deserialization)
5. Viết tests và manual test plan

## Tasks

- [ ] 1. Cài đặt dependencies và chuẩn bị môi trường
  - Cài đặt thư viện `rapidfuzz` cho fuzzy string matching: `pip install rapidfuzz`
  - Verify thư viện đã được cài đặt thành công
  - _Requirements: 1.1, 2.1_

- [ ] 2. Thêm fields mới vào AutoAction dataclass
  - [ ] 2.1 Thêm 7 fields vào AutoAction trong `src/logic/action_type.py`
    - `event_tracking_enabled: bool = False`
    - `event_ocr_pattern: str = ""`
    - `event_match_threshold: float = 100.0`
    - `event_delay_threshold: int = 0`
    - `event_reset_interval: int = 15`
    - `event_telegram_message: str = ""`
    - ROI sẽ được lấy từ Teaching image (teaching_corner_x1, y1, x2, y2)
    - Thêm type hints và docstrings đầy đủ
    - _Requirements: 2.1, 2.2, 2.3_

- [ ] 3. Update ToolManager để persist Event Tracking settings
  - [ ] 3.1 Thêm serialization trong `Tool._action_to_dict()`
    - Serialize 7 fields mới vào JSON dict
    - Xử lý None values và default values
    - Convert tuple thành list cho JSON compatibility
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ] 3.2 Thêm deserialization trong `Tool.from_dict()`
    - Load 5 fields từ JSON dict
    - Set default values nếu field không tồn tại (backward compatibility)
    - ROI sẽ được lấy từ Teaching image, không cần convert event_roi_coordinates
    - _Requirements: 2.1, 2.2, 2.3_

- [ ] 4. Checkpoint - Verify data persistence
  - Test: Tạo action với Event Tracking settings → Save tool → Close app → Reopen → Verify settings persist
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Update PassiveReadSettingsDialog UI
  - [ ] 5.1 Thêm "Event Tracking" vào dropdown "Chế độ hoạt động"
    - Update `passive_mode_combo` để có 3 options: "Đọc dữ liệu", "Phát hiện hình ảnh", "Event Tracking"
    - _Requirements: 4.1_
  
  - [ ] 5.2 Implement `_add_event_tracking_section()`
    - Tạo QGroupBox "🔔 Event Tracking Settings"
    - Thêm UI controls:
      - ROI Settings: "Set ROI..." button, "Clear" button, ROI label
      - OCR Pattern: QLineEdit với placeholder
      - Match Threshold: QDoubleSpinBox (0-100%)
      - Delay Threshold: QSpinBox (0-3600 seconds)
      - Reset Interval: QSpinBox (0-1440 minutes)
      - Telegram Message: QLineEdit với placeholder
      - Configure Algorithms button
      - Selected Algorithms: QListWidget
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ] 5.3 Implement `_on_passive_mode_changed()`
    - Show/hide groups based on mode selection
    - Mode 0: Show two_column_widget (Đọc dữ liệu)
    - Mode 1: Show detect_group (Phát hiện hình ảnh)
    - Mode 2: Show event_tracking_group (Event Tracking)
    - _Requirements: 4.1_
  
  - [ ] 5.4 Implement Event ROI teaching methods
    - `_set_event_roi()`: Open ImageCaptureDialog để teaching ROI
    - `_clear_event_roi()`: Clear ROI và update label
    - Update `event_roi_label` để hiển thị tọa độ hoặc "Not set"
    - _Requirements: 4.2_
  
  - [ ] 5.5 Implement Event OCR algorithms config
    - `_open_event_ocr_config()`: Open Multi-Image Algorithm Testing Dialog
    - `_update_event_algorithms_display()`: Update QListWidget với algorithms đã chọn
    - _Requirements: 4.3_
  
  - [ ] 5.6 Update `_load_settings()` để load Event Tracking settings
    - Load 7 fields từ action
    - Update UI controls với giá trị đã load
    - Update event_roi_label
    - Call `_update_event_algorithms_display()`
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ] 5.7 Update `get_settings()` để return Event Tracking settings
    - Add passive_mode mapping: 2 → "event_tracking"
    - Return dict với 7 fields mới
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ] 5.8 Update `_validate_settings()` để validate Event Tracking
    - Check OCR Pattern không trống
    - Check Telegram Message không trống
    - Check ROI đã được teaching
    - Check Telegram đã được cấu hình
    - _Requirements: 3.3.6_

- [ ] 6. Checkpoint - Verify UI functionality
  - Test: Open Passive Read Settings → Select "Event Tracking" → Verify UI shows correct controls
  - Test: Set ROI, configure algorithms, fill in settings → Save → Reopen → Verify settings persist
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement Event Tracking logic trong SystemExecutor
  - [ ] 7.1 Thêm state management cho Event Tracking
    - Add `_event_sent_messages: dict[str, float] = {}` trong `__init__()`
    - Dict lưu {message_text: last_sent_timestamp}
    - _Requirements: 3.1.5_
  
  - [ ] 7.2 Update `_execute_read_passive()` để check Event Tracking mode
    - Check `action.event_tracking_enabled` hoặc `action.passive_mode == "event_tracking"`
    - Nếu True: Call `_execute_event_tracking(action)`
    - Nếu False: Execute normal passive read logic (existing code)
    - _Requirements: 3.1_
  
  - [ ] 7.3 Implement `_execute_event_tracking()` method
    - Bước 1: Capture screenshot từ Teaching image ROI (teaching_corner_x1, y1, x2, y2)
    - Bước 2: Apply OCR preprocessing nếu có (sử dụng OCRPreprocessor)
    - Bước 3: Read text với OCR engine (sử dụng OCRFactory)
    - Bước 4: Parse từng dòng text với `_parse_event_pattern()`
    - Bước 5: Nếu match, check duplicate với `_check_event_duplicate()`
    - Bước 6: Nếu không duplicate, wait delay_threshold
    - Bước 7: Send Telegram với `_send_event_telegram()`
    - Bước 8: Save to sent list
    - Bước 9: Cleanup old entries với `_cleanup_event_sent_messages()`
    - _Requirements: 3.1_
  
  - [ ] 7.4 Implement `_parse_event_pattern()` method
    - Convert pattern với placeholder thành regex
    - Thay {variable_name} → (?P<variable_name>.+?) cho text
    - Thay {variable_name} → (?P<variable_name>\d+) cho numbers
    - Nếu match_threshold == 100: Sử dụng exact regex matching
    - Nếu match_threshold < 100: Sử dụng rapidfuzz.fuzz.ratio() cho fuzzy matching
    - Return dict với extracted variables hoặc None
    - _Requirements: 3.1.2_
  
  - [ ] 7.5 Implement `_check_event_duplicate()` method
    - Check nếu message text đã tồn tại trong `_event_sent_messages`
    - Nếu reset_interval == 0: Return True (skip forever)
    - Nếu reset_interval > 0: Check (now - last_sent_time) >= reset_interval
    - Return True nếu duplicate (should skip), False nếu new (should send)
    - _Requirements: 3.1.3_
  
  - [ ] 7.6 Implement `_send_event_telegram()` method
    - Replace placeholders trong telegram_message với extracted variables
    - Send message qua TelegramNotifier
    - Retry 3 lần với delay 1 giây nếu fail
    - Return True nếu success, False nếu fail
    - _Requirements: 3.1.4_
  
  - [ ] 7.7 Implement `_cleanup_event_sent_messages()` method
    - Remove entries cũ hơn reset_interval * 2
    - Giới hạn max size của dict (1000 entries)
    - _Requirements: 1.4.3_

- [ ] 8. Checkpoint - Verify Event Tracking logic
  - Test: Create tool với Event Tracking → Run tool → Verify OCR reads text → Verify pattern matching → Verify Telegram sent
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Viết unit tests
  - [ ] 9.1 Test AutoAction fields
    - Test default values của 7 fields mới
    - Test type hints
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ] 9.2 Test ToolManager serialization/deserialization
    - Test `_action_to_dict()` serialize đúng 7 fields
    - Test `from_dict()` deserialize đúng 7 fields
    - Test backward compatibility (old JSON không có fields mới)
    - Test None values và default values
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ] 9.3 Test pattern parsing
    - Test `_parse_event_pattern()` với exact matching (100%)
    - Test với fuzzy matching (< 100%)
    - Test với multi-line text
    - Test với text không khớp pattern
    - Test extract variables từ pattern
    - _Requirements: 3.1.2, 3.2.1, 3.2.3_
  
  - [ ] 9.4 Test duplicate detection
    - Test `_check_event_duplicate()` với reset_interval = 0
    - Test với reset_interval > 0 và chưa đủ thời gian
    - Test với reset_interval > 0 và đã quá thời gian
    - Test với message mới (chưa gửi bao giờ)
    - _Requirements: 3.1.3, 3.2.5_
  
  - [ ] 9.5 Test cleanup logic
    - Test `_cleanup_event_sent_messages()` remove old entries
    - Test giới hạn max size (1000 entries)
    - _Requirements: 1.4.3_

- [ ] 10. Viết integration tests
  - [ ] 10.1 Test end-to-end Event Tracking flow
    - Setup: Create action với Event Tracking settings
    - Execute: Run `_execute_event_tracking()`
    - Verify: OCR reads text → Pattern matches → Telegram sent → Saved to sent list
    - _Requirements: 3.1_
  
  - [ ] 10.2 Test với OCR preprocessing
    - Setup: Configure OCR algorithms (upscale, contrast, sharpen)
    - Execute: Run Event Tracking
    - Verify: Preprocessing applied → OCR reads text correctly
    - _Requirements: 3.1.1_
  
  - [ ] 10.3 Test duplicate prevention
    - Setup: Send same message twice
    - Execute: Run Event Tracking twice
    - Verify: First message sent, second message skipped
    - _Requirements: 3.1.3, 3.2.5_
  
  - [ ] 10.4 Test reset interval
    - Setup: Send message → Wait reset_interval → Send same message again
    - Execute: Run Event Tracking twice với delay
    - Verify: Both messages sent (reset interval expired)
    - _Requirements: 3.1.3, 3.2.5_

- [ ] 11. Viết manual test plan
  - [ ] 11.1 Tạo file `docs/MANUAL_TEST_EVENT_TRACKING.md`
    - Test Case 1: Teaching ROI và configure algorithms
    - Test Case 2: Set pattern và test với real game notification
    - Test Case 3: Test delay threshold
    - Test Case 4: Test reset interval với duplicate messages
    - Test Case 5: Test fuzzy matching với match threshold < 100%
    - Test Case 6: Test Telegram notification
    - Test Case 7: Test data persistence (save → close → reopen)
    - Mỗi test case có: Mục đích, Điều kiện tiên quyết, Các bước thực hiện, Kết quả mong đợi
    - _Requirements: All_

- [ ] 12. Final checkpoint - Ensure all tests pass
  - Run all unit tests
  - Run all integration tests
  - Verify manual test plan is complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Feature này không có property-based tests vì logic phức tạp và phụ thuộc vào external services (OCR, Telegram)
- Unit tests validate specific examples và edge cases
- Integration tests validate end-to-end flows
- Manual test plan để user tự test với real game notifications
