# Requirements Document

## Introduction

Feature này bao gồm 2 tính năng chính:
1. **Test Action Button**: Cho phép chạy thử 1 action riêng lẻ để kiểm tra cấu hình (teaching image, tọa độ click, v.v.)
2. **Tool Status Panel**: Hiển thị trạng thái real-time của tool đang chạy với danh sách action và thời gian thực thi

## Glossary

- **Test_Action_System**: Hệ thống cho phép chạy thử 1 action riêng lẻ
- **Status_Panel**: Panel hiển thị trạng thái tool đang chạy
- **Action**: Một bước trong tool (KEYBOARD, MOUSE_CLICK, IMAGE_DETECT, READ_PASSIVE, WAIT)
- **Tool**: Tập hợp các action được thực thi tuần tự
- **Window_Handle**: Handle của window game đang được chọn

## Requirements

### Requirement 1: Test Action Button trong ToolEditorWindow

**User Story:** Là một user, tôi muốn có nút Test cạnh mỗi action trong danh sách, để tôi có thể kiểm tra action đó hoạt động đúng không trước khi chạy full tool.

#### Acceptance Criteria

1. THE ToolEditorWindow SHALL hiển thị nút "Test" cạnh mỗi action trong danh sách actions
2. WHEN user click nút Test mà chưa chọn window game, THEN Test_Action_System SHALL hiển thị dialog thông báo "Vui lòng chọn window game trước"
3. WHEN user click nút Test và đã chọn window game, THEN Test_Action_System SHALL dừng tool đang chạy (nếu có)
4. WHEN user click nút Test và đã chọn window game, THEN Test_Action_System SHALL focus vào window game trước khi thực thi
5. WHEN Test_Action_System thực thi action, THEN Test_Action_System SHALL thực hiện đầy đủ như tool bình thường (click chuột, ấn phím, v.v.)
6. WHEN Test_Action_System thực thi action, THEN Test_Action_System SHALL log kết quả vào console (thành công/thất bại)
7. WHEN Test_Action_System đang chạy, THEN Test_Action_System SHALL hiển thị thời gian chạy / thời gian timeout

### Requirement 2: Test Action Button trong ActionConfigDialog

**User Story:** Là một user, tôi muốn có nút Test trong dialog cấu hình action, để tôi có thể kiểm tra ngay sau khi cấu hình xong.

#### Acceptance Criteria

1. THE ActionConfigDialog SHALL hiển thị nút "Test" cạnh nút "Cài đặt"
2. WHEN user click nút Test trong ActionConfigDialog, THEN Test_Action_System SHALL áp dụng các acceptance criteria của Requirement 1

### Requirement 3: Tool Status Panel - Expandable Section

**User Story:** Là một user, tôi muốn xem danh sách action của tool đang chạy và biết action nào đang thực thi, để tôi có thể theo dõi tiến trình.

#### Acceptance Criteria

1. THE MainWindow SHALL có nút "Xem process" dưới danh sách tool đang chạy
2. WHEN user click nút "Xem process", THEN Status_Panel SHALL mở rộng hiển thị danh sách action của tool đang chạy
3. WHEN user click nút "Xem process" lần nữa, THEN Status_Panel SHALL thu gọn lại
4. THE Status_Panel SHALL hiển thị tên của từng action trong tool
5. WHEN một action đang được thực thi, THEN Status_Panel SHALL highlight action đó bằng màu dễ nhìn
6. WHEN một action đang được thực thi, THEN Status_Panel SHALL hiển thị thời gian đang chạy của action đó
7. WHEN tool chuyển sang chu kỳ mới (loop), THEN Status_Panel SHALL reset thời gian hiển thị về 0

### Requirement 4: Real-time Update

**User Story:** Là một user, tôi muốn Status Panel cập nhật real-time, để tôi có thể theo dõi chính xác action nào đang chạy.

#### Acceptance Criteria

1. WHEN tool bắt đầu thực thi một action, THEN Status_Panel SHALL cập nhật UI ngay lập tức (highlight action mới)
2. WHEN tool hoàn thành một action, THEN Status_Panel SHALL cập nhật UI ngay lập tức (bỏ highlight, hiển thị thời gian)
3. THE Status_Panel SHALL sử dụng signal/slot để đảm bảo thread-safe khi cập nhật UI

### Requirement 5: Conflict Handling

**User Story:** Là một user, tôi muốn hệ thống tự động xử lý conflict giữa Test Action và Tool đang chạy, để tránh lỗi.

#### Acceptance Criteria

1. WHEN user click Test Action trong khi tool đang chạy, THEN Test_Action_System SHALL dừng tool đang chạy trước khi test
2. WHEN user chạy tool trong khi Test Action đang chạy, THEN Tool_Runner SHALL dừng Test Action trước khi chạy tool
3. WHEN conflict xảy ra, THEN System SHALL log thông báo về việc dừng process cũ

### Requirement 6: Status Panel khi không có tool chạy

**User Story:** Là một user, tôi muốn Status Panel vẫn hiển thị danh sách action nhưng không highlight gì, để tôi biết tool không đang chạy.

#### Acceptance Criteria

1. WHEN không có tool nào đang chạy, THEN Status_Panel SHALL hiển thị danh sách action mà không highlight action nào
2. WHEN không có tool nào đang chạy, THEN Status_Panel SHALL không hiển thị thời gian chạy

## Input/Output

**Input:**
- User click nút Test (trong ToolEditorWindow hoặc ActionConfigDialog)
- User click nút "Xem process" để toggle Status Panel
- Signal từ engine khi action bắt đầu/kết thúc

**Output:**
- Log kết quả test action vào console
- UI cập nhật real-time (highlight action, thời gian chạy)
- Dialog thông báo khi chưa chọn window game

## Technical Notes

- Sử dụng PyQt6 signal/slot cho thread-safe UI update
- Test Action sẽ tạo temporary executor để chạy 1 action
- Status Panel sử dụng QTimer để cập nhật thời gian chạy mỗi 100ms
- Không cần hiển thị debug info (best_score, threshold) trong phiên bản này
