# Requirements Document

## Feature: Tool Copy Feature

## 1. Tổng quan
Feature cho phép user sao chép (duplicate) một tool hiện có với tên mới, tạo ra bản copy hoàn toàn độc lập với UUID riêng và deep copy toàn bộ dữ liệu bao gồm cả teaching images.

## 2. User Stories
- Là một user, tôi muốn sao chép tool hiện có, để tôi có thể tạo variant mới mà không phải tạo lại từ đầu
- Là một user, tôi muốn đặt tên khác cho tool copy, để tôi có thể phân biệt với tool gốc
- Là một user, tôi muốn tool copy hoàn toàn độc lập, để việc chỉnh sửa không ảnh hưởng tool gốc

## 3. Acceptance Criteria

### Requirement 1: Copy Tool Button
**User Story:** Là một user, tôi muốn có button "Sao chép Tool" trên home screen, để tôi có thể dễ dàng copy tool hiện tại.

#### Acceptance Criteria
1. WHEN user mở home screen THEN hệ thống SHALL hiển thị button "Sao chép Tool" giữa button "Sửa Tool" và "Xóa Tool"
2. WHEN user chưa chọn tool nào THEN button "Sao chép Tool" SHALL bị disable
3. WHEN user đã chọn tool THEN button "Sao chép Tool" SHALL được enable
4. WHEN user click button "Sao chép Tool" THEN hệ thống SHALL mở dialog nhập tên tool mới

### Requirement 2: Tool Name Input Dialog
**User Story:** Là một user, tôi muốn nhập tên cho tool copy, để tôi có thể đặt tên phù hợp với mục đích sử dụng.

#### Acceptance Criteria
1. WHEN dialog mở THEN hệ thống SHALL hiển thị input field với placeholder text "Nhập tên tool mới"
2. WHEN user nhập tên trống hoặc chỉ có khoảng trắng THEN hệ thống SHALL hiển thị lỗi "Tên tool không được để trống"
3. WHEN user nhập tên đã tồn tại THEN hệ thống SHALL hiển thị lỗi "Tên tool đã tồn tại"
4. WHEN user nhập tên hợp lệ và click OK THEN hệ thống SHALL tạo tool copy và đóng dialog
5. WHEN user click Cancel THEN hệ thống SHALL đóng dialog mà không tạo tool

### Requirement 3: Deep Copy Tool Data
**User Story:** Là một user, tôi muốn tool copy chứa toàn bộ dữ liệu của tool gốc, để tôi có thể sử dụng ngay mà không cần cấu hình lại.

#### Acceptance Criteria
1. WHEN tool được copy THEN hệ thống SHALL tạo UUID mới cho tool copy
2. WHEN tool được copy THEN hệ thống SHALL copy toàn bộ settings (loop, timeout, notification, etc.)
3. WHEN tool được copy THEN hệ thống SHALL copy toàn bộ actions với tất cả properties
4. WHEN tool được copy THEN hệ thống SHALL copy toàn bộ teaching images vào thư mục mới
5. WHEN tool được copy THEN tool copy SHALL hoàn toàn độc lập với tool gốc

### Requirement 4: Teaching Images Copy
**User Story:** Là một user, tôi muốn teaching images được copy cùng với tool, để tool copy có thể hoạt động ngay lập tức.

#### Acceptance Criteria
1. WHEN tool có teaching images THEN hệ thống SHALL copy tất cả images từ thư mục `images/{old_tool_id}/` sang `images/{new_tool_id}/`
2. WHEN tool copy được tạo THEN tất cả image paths trong actions SHALL được update để trỏ đến thư mục mới
3. WHEN không có teaching images THEN hệ thống SHALL tạo tool copy bình thường mà không báo lỗi

### Requirement 5: User Feedback
**User Story:** Là một user, tôi muốn biết kết quả copy tool, để tôi biết thao tác đã thành công hay thất bại.

#### Acceptance Criteria
1. WHEN copy tool thành công THEN hệ thống SHALL hiển thị message "Đã sao chép tool thành công: [tên_tool_mới]"
2. WHEN copy tool thất bại THEN hệ thống SHALL hiển thị message lỗi cụ thể
3. WHEN copy tool thành công THEN tool combo SHALL được refresh và chọn tool mới
4. WHEN copy tool thành công THEN tool mới SHALL xuất hiện trong danh sách tools

## 4. Input/Output

**Input:**
- Tool hiện tại được chọn trong combo
- Tên mới cho tool copy từ dialog

**Output:**
- Tool mới được tạo với UUID riêng
- File JSON mới trong thư mục `tools/`
- Thư mục images mới (nếu có teaching images)
- Tool combo được refresh với tool mới

## 5. Sơ đồ khối (Text-based)

```
┌─────────────────┐
│   User clicks   │
│ "Sao chép Tool" │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Open Dialog    │
│ "Nhập tên mới"  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Validate Name   │
│ (unique, not    │
│    empty)       │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Deep Copy      │
│ Tool + Images   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Generate UUID   │
│ Save to JSON    │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Refresh Combo   │
│ Show Success    │
└─────────────────┘
```

## 6. Technical Notes

### Data Persistence
- Tool copy phải được lưu vào file JSON riêng với UUID mới
- Tất cả references đến images phải được update
- Tool copy hoàn toàn độc lập với tool gốc

### Image Handling
- Copy physical files từ `images/{old_id}/` sang `images/{new_id}/`
- Update image paths trong action data
- Handle trường hợp không có images

### Validation Rules
- Tên tool không được rỗng hoặc chỉ có khoảng trắng
- Tên tool phải unique trong hệ thống
- Tool gốc phải tồn tại và load được

### Error Handling
- Handle lỗi file I/O khi copy images
- Handle lỗi JSON serialization
- Handle lỗi validation tên tool
- Rollback nếu copy thất bại (xóa files đã tạo)

### UI Integration
- Button placement giữa "Sửa Tool" và "Xóa Tool"
- Enable/disable button dựa trên tool selection
- Dialog modal với validation real-time
- Success/error messages rõ ràng