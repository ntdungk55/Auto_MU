# Requirements Document

## Introduction

Feature khóa input (chuột + bàn phím) khi thực hiện action để tránh user vô tình di chuột/ấn phím làm gián đoạn automation. Có hotkey khẩn cấp để unlock và dừng tool hoàn toàn.

## Glossary

- **Input Blocking**: Khóa chuột và bàn phím của user (không ảnh hưởng đến automation)
- **Block Duration**: Thời gian tối đa khóa input cho mỗi action (0.1s - 10s)
- **Emergency Hotkey**: Phím F12 để unlock và dừng tool
- **Tool Settings Dialog**: Dialog cấu hình settings cho tool
- **BlockInput() API**: Windows API để khóa input từ user

## Requirements

### Requirement 1: Checkbox và Setting trong Tool Settings

**User Story:** Là một user, tôi muốn bật/tắt khóa input khi thực hiện action, để tránh vô tình làm gián đoạn automation.

#### Acceptance Criteria

1. WHEN user mở Tool Settings Dialog, THE System SHALL hiển thị checkbox "Khóa input khi thực hiện action"
2. WHEN user mở Tool Settings Dialog, THE System SHALL hiển thị spinbox "Thời gian khóa tối đa"
3. THE spinbox SHALL có range từ 0.1 đến 10.0 giây
4. THE spinbox SHALL có giá trị mặc định là 3.0 giây
5. THE spinbox SHALL có suffix " giây"
6. WHEN checkbox được check, THE System SHALL hiển thị thông báo: "Ấn F12 để dừng hoàn toàn"
7. WHEN checkbox được uncheck, THE System SHALL ẩn thông báo
8. WHEN user thay đổi setting, THE System SHALL lưu ngay lập tức

### Requirement 2: Data Persistence

**User Story:** Là một developer, tôi muốn setting được lưu vào JSON, để setting không bị mất khi restart app.

#### Acceptance Criteria

1. THE System SHALL thêm field "block_input_enabled" vào Tool class
2. THE System SHALL thêm field "block_input_duration" vào Tool class
3. THE System SHALL lưu "block_input_enabled" vào tool JSON file trong method to_dict()
4. THE System SHALL lưu "block_input_duration" vào tool JSON file trong method to_dict()
5. THE System SHALL load "block_input_enabled" từ tool JSON file trong method from_dict()
6. THE System SHALL load "block_input_duration" từ tool JSON file trong method from_dict()
7. WHEN tool được save, THE settings SHALL được persist
8. WHEN tool được load, THE settings SHALL được restore đúng
9. THE "block_input_enabled" SHALL default to False
10. THE "block_input_duration" SHALL default to 3.0

### Requirement 3: Block Input khi thực hiện Action

**User Story:** Là một user, tôi muốn input bị khóa khi action đang chạy, để tránh vô tình làm gián đoạn.

#### Acceptance Criteria

1. WHEN "block_input_enabled" = True, THE System SHALL khóa input trước khi thực hiện action
2. WHEN "block_input_enabled" = False, THE System SHALL không khóa input
3. THE System SHALL khóa input cho tất cả action types (KEYBOARD, MOUSE_CLICK, IMAGE_DETECT)
4. THE System SHALL khóa tối đa "block_input_duration" giây
5. WHEN action kết thúc trước timeout, THE System SHALL unlock ngay lập tức
6. WHEN action kết thúc sau timeout, THE System SHALL đã unlock rồi
7. THE System SHALL KHÔNG khóa input trong thời gian delay (action.delay)
8. THE System SHALL log "🔒 Đã khóa input" khi khóa
9. THE System SHALL log "🔓 Đã mở khóa input" khi unlock

### Requirement 4: Emergency Hotkey

**User Story:** Là một user, tôi muốn có cách thoát khẩn cấp, để dừng tool khi cần thiết.

#### Acceptance Criteria

1. THE System SHALL monitor hotkey F12 khi tool đang chạy
2. WHEN F12 được ấn, THE System SHALL unlock input ngay lập tức
3. WHEN F12 được ấn, THE System SHALL dừng tool hoàn toàn (stop completely)
4. THE System SHALL log "⚠️ Emergency stop: Đã dừng tool do hotkey" khi hotkey được ấn
5. THE hotkey monitoring SHALL chạy trong background thread
6. THE hotkey monitoring SHALL dừng khi tool dừng

### Requirement 5: Error Handling và Safety

**User Story:** Là một developer, tôi muốn đảm bảo input luôn được unlock, để tránh user bị "mắc kẹt".

#### Acceptance Criteria

1. THE System SHALL wrap tất cả BlockInput() calls trong try-except-finally
2. THE finally block SHALL luôn unlock input
3. WHEN BlockInput() fail, THE System SHALL log warning
4. WHEN BlockInput() fail, THE System SHALL tiếp tục chạy tool bình thường
5. WHEN tool crash, THE System SHALL unlock input trước khi exit
6. WHEN tool stop, THE System SHALL unlock input trước khi exit
7. WHEN tool pause, THE System SHALL unlock input trước khi pause
8. THE System SHALL KHÔNG crash nếu BlockInput() API fail

### Requirement 6: Windows BlockInput() API Integration

**User Story:** Là một developer, tôi muốn sử dụng Windows API để khóa input, để đảm bảo tính chính xác.

#### Acceptance Criteria

1. THE System SHALL sử dụng ctypes.windll.user32.BlockInput()
2. THE System SHALL call BlockInput(True) để khóa
3. THE System SHALL call BlockInput(False) để unlock
4. THE System SHALL wrap API call trong try-except
5. WHEN API call fail, THE System SHALL return False
6. WHEN API call success, THE System SHALL return True

### Requirement 7: Thread Safety

**User Story:** Là một developer, tôi muốn đảm bảo thread-safe, để tránh race condition.

#### Acceptance Criteria

1. THE System SHALL sử dụng threading.Event() để coordinate giữa threads
2. THE hotkey monitoring thread SHALL set event khi hotkey được ấn
3. THE main thread SHALL check event và unlock input
4. THE System SHALL đảm bảo chỉ 1 thread unlock input tại 1 thời điểm
5. THE System SHALL cleanup threads khi tool dừng

### Requirement 8: Logging và User Feedback

**User Story:** Là một user, tôi muốn biết khi nào input bị khóa/mở khóa, để hiểu trạng thái hệ thống.

#### Acceptance Criteria

1. WHEN input được khóa, THE System SHALL log "🔒 Đã khóa input (X giây)"
2. WHEN input được mở khóa, THE System SHALL log "🔓 Đã mở khóa input"
3. WHEN BlockInput() fail, THE System SHALL log "⚠️ Không thể khóa input (cần quyền admin?)"
4. WHEN emergency hotkey được ấn, THE System SHALL log "⚠️ Emergency stop: Đã dừng tool do hotkey"
5. THE logs SHALL có màu sắc rõ ràng (green cho unlock, orange cho lock, red cho emergency)

### Requirement 9: Không khóa trong Delay

**User Story:** Là một user, tôi không muốn input bị khóa trong thời gian delay, để có thể tương tác khi cần.

#### Acceptance Criteria

1. WHEN action.delay > 0, THE System SHALL unlock input trước khi delay
2. WHEN delay kết thúc, THE System SHALL KHÔNG khóa lại input
3. THE System SHALL chỉ khóa input khi thực hiện action (click, keyboard, detect)
4. THE System SHALL KHÔNG khóa input trong loop_pre_delay
5. THE System SHALL KHÔNG khóa input trong loop_post_delay

### Requirement 10: Khóa theo Duration Setting

**User Story:** Là một user, tôi muốn tự điều chỉnh thời gian khóa, để phù hợp với từng use case.

#### Acceptance Criteria

1. WHEN action chạy < block_input_duration, THE System SHALL unlock khi action xong
2. WHEN action chạy > block_input_duration, THE System SHALL unlock sau block_input_duration
3. THE System SHALL KHÔNG lặp lại khóa (khóa 1 lần duy nhất mỗi action)
4. WHEN IMAGE_DETECT timeout 30s và block_input_duration = 3s, THE System SHALL khóa 3s rồi unlock
5. THE remaining 27s của IMAGE_DETECT SHALL chạy KHÔNG khóa input

