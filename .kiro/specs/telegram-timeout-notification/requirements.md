# Requirements Document

## Introduction

Feature thông báo Telegram khi tool dừng hoàn toàn do timeout. Giúp user được thông báo ngay lập tức khi tool gặp lỗi timeout mà không cần theo dõi màn hình liên tục.

## Glossary

- **Tool**: Một automation workflow gồm nhiều actions
- **Timeout**: Trạng thái khi action không tìm thấy hình ảnh sau thời gian chờ
- **Stop Completely**: Tool dừng hoàn toàn và reset về đầu (không phải pause)
- **Telegram Notification**: Tin nhắn gửi qua Telegram Bot API
- **Tool Settings Dialog**: Dialog cấu hình settings cho tool
- **Deduplication**: Cơ chế tránh gửi thông báo trùng lặp

## Requirements

### Requirement 1: Checkbox trong Tool Settings

**User Story:** Là một user, tôi muốn bật/tắt thông báo Telegram khi timeout, để tôi có thể nhận thông báo khi tool gặp lỗi.

#### Acceptance Criteria

1. WHEN user mở Tool Settings Dialog, THE System SHALL hiển thị checkbox "Thông báo Telegram khi timeout"
2. WHEN user check vào checkbox mà Telegram chưa được cấu hình, THE System SHALL hiển thị message box thông báo
3. WHEN message box hiển thị, THE System SHALL cung cấp 2 options: "Mở cấu hình Telegram" và "Hủy"
4. WHEN user chọn "Mở cấu hình Telegram", THE System SHALL mở TelegramConfigDialog
5. WHEN user chọn "Hủy", THE System SHALL giữ checkbox ở trạng thái unchecked
6. WHEN user check vào checkbox mà Telegram đã được cấu hình, THE System SHALL cho phép check và lưu setting
7. WHEN user uncheck checkbox, THE System SHALL lưu setting ngay lập tức

### Requirement 2: Kiểm tra Telegram Configuration

**User Story:** Là một developer, tôi muốn kiểm tra Telegram đã được cấu hình chưa, để đảm bảo notification có thể gửi được.

#### Acceptance Criteria

1. THE System SHALL kiểm tra bot_token có tồn tại trong app_state.json
2. THE System SHALL kiểm tra chat_id có tồn tại trong app_state.json
3. WHEN cả bot_token và chat_id đều tồn tại và không rỗng, THE System SHALL coi Telegram đã được cấu hình
4. WHEN bot_token hoặc chat_id không tồn tại hoặc rỗng, THE System SHALL coi Telegram chưa được cấu hình

### Requirement 3: Gửi Telegram Notification khi Timeout

**User Story:** Là một user, tôi muốn nhận thông báo Telegram khi tool timeout, để tôi biết tool đã dừng mà không cần theo dõi màn hình.

#### Acceptance Criteria

1. WHEN tool timeout và dừng hoàn toàn (stop completely), THE System SHALL kiểm tra setting "notify_on_timeout"
2. WHEN "notify_on_timeout" = True, THE System SHALL gửi Telegram notification
3. WHEN "notify_on_timeout" = False, THE System SHALL không gửi notification
4. THE notification SHALL chứa tool name
5. THE notification SHALL chứa action name bị timeout
6. THE notification SHALL có format rõ ràng và dễ đọc

### Requirement 4: Deduplication

**User Story:** Là một user, tôi không muốn nhận nhiều thông báo trùng lặp, để tránh spam.

#### Acceptance Criteria

1. THE System SHALL lưu timestamp của lần gửi notification cuối cùng cho mỗi tool
2. WHEN tool timeout lần thứ 2 trong vòng 60 giây, THE System SHALL không gửi notification
3. WHEN tool timeout sau 60 giây kể từ lần gửi cuối, THE System SHALL gửi notification mới
4. THE System SHALL lưu deduplication state trong memory (không cần persist)

### Requirement 5: Data Persistence

**User Story:** Là một developer, tôi muốn setting được lưu vào JSON, để setting không bị mất khi restart app.

#### Acceptance Criteria

1. THE System SHALL thêm field "notify_on_timeout" vào Tool class
2. THE System SHALL lưu "notify_on_timeout" vào tool JSON file trong method to_dict()
3. THE System SHALL load "notify_on_timeout" từ tool JSON file trong method from_dict()
4. WHEN tool được save, THE "notify_on_timeout" setting SHALL được persist
5. WHEN tool được load, THE "notify_on_timeout" setting SHALL được restore đúng

### Requirement 6: Error Handling

**User Story:** Là một developer, tôi muốn xử lý lỗi khi gửi Telegram, để tránh crash tool.

#### Acceptance Criteria

1. WHEN gửi Telegram notification fail, THE System SHALL log error
2. WHEN gửi Telegram notification fail, THE System SHALL không crash tool
3. WHEN gửi Telegram notification fail, THE System SHALL tiếp tục dừng tool bình thường
4. THE System SHALL wrap Telegram API call trong try-except block

### Requirement 7: Thread Safety

**User Story:** Là một developer, tôi muốn đảm bảo thread-safe, để tránh race condition.

#### Acceptance Criteria

1. WHEN gửi notification từ engine thread, THE System SHALL không block UI thread
2. WHEN kiểm tra Telegram config từ UI thread, THE System SHALL không block UI
3. THE System SHALL sử dụng Qt signals để communicate giữa threads nếu cần

### Requirement 8: Chỉ gửi khi Stop Completely

**User Story:** Là một user, tôi chỉ muốn nhận thông báo khi tool dừng hẳn, không phải khi restart hoặc goto step.

#### Acceptance Criteria

1. WHEN timeout và tool có "continue_on_timeout" = True, THE System SHALL không gửi notification
2. WHEN timeout và tool có "timeout_goto_enabled" = True, THE System SHALL không gửi notification
3. WHEN timeout và tool có "restart_on_timeout" = True, THE System SHALL không gửi notification
4. WHEN timeout và tool stop completely (mặc định), THE System SHALL gửi notification (nếu enabled)
