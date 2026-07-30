# Implementation Plan: Passive Reading Dialog Improvement

## Overview

Cải thiện giao diện dialog cấu hình action "Đọc thụ động" bằng cách ẩn timeout widget (chứa "Thời gian tối đa chờ" và "Chu kỳ kiểm tra") khi người dùng chọn action type READ_PASSIVE.

## Tasks

- [x] 1. Sửa logic hiển thị timeout widget trong action_config_dialog.py
  - Thay đổi dòng 570 để loại bỏ READ_PASSIVE khỏi danh sách action types hiển thị timeout_widget
  - Đảm bảo timeout_widget vẫn hiển thị cho MOUSE_CLICK và IMAGE_DETECT
  - _Requirements: 2.1, 2.2_

- [ ] 1.1 Viết unit test cho logic hiển thị timeout widget
  - Test timeout_widget bị ẩn khi action_type = READ_PASSIVE
  - Test timeout_widget hiển thị khi action_type = MOUSE_CLICK hoặc IMAGE_DETECT
  - _Requirements: 2.1, 2.2_

- [ ] 2. Kiểm tra và đảm bảo tương thích ngược
  - Verify rằng việc ẩn timeout_widget không ảnh hưởng đến việc lưu/load action data
  - Đảm bảo existing READ_PASSIVE actions vẫn hoạt động bình thường
  - _Requirements: 3.4_

- [ ] 2.1 Viết property test cho data persistence
  - **Property 3: Data Persistence Integrity**
  - **Validates: Requirements 1.2, 3.3**

- [ ] 3. Test UI behavior khi chuyển đổi action types
  - Verify UI updates correctly khi user chuyển từ READ_PASSIVE sang action type khác
  - Verify UI updates correctly khi user chuyển từ action type khác sang READ_PASSIVE
  - _Requirements: 3.2_

- [ ] 3.1 Viết property test cho action type toggle behavior
  - **Property 2: Action Type Toggle Behavior**
  - **Validates: Requirements 2.2, 3.2**

- [ ] 4. Checkpoint - Đảm bảo tất cả tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 4.1 Viết integration test cho complete dialog workflow
  - Test toàn bộ workflow: khởi tạo dialog → chọn READ_passive → cấu hình → save → load
  - Verify UI state consistency throughout the workflow
  - _Requirements: 1.1, 2.1, 3.1_

- [ ] 5. Final validation và cleanup
  - Manual test với existing READ_PASSIVE actions
  - Verify không có regression với other action types
  - _Requirements: 3.4_

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases