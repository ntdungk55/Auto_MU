# Requirements Document

## Introduction

Cải thiện giao diện dialog tạo action cho chức năng "Đọc thụ động" để làm cho các tùy chọn cấu hình rõ ràng và dễ hiểu hơn cho người dùng.

## Glossary

- **Dialog**: Cửa sổ giao diện để tạo và cấu hình action
- **Action_Đọc_Thụ_Động**: Chức năng đọc thụ động trong ứng dụng
- **Chu_Kỳ_Chụp**: Khoảng thời gian giữa các lần chụp ảnh
- **Chu_Kỳ_Xử_Lý**: Khoảng thời gian giữa các lần xử lý ảnh

## Requirements

### Requirement 1: Cập nhật Label Chu Kỳ

**User Story:** Là người dùng, tôi muốn thấy label rõ ràng về chu kỳ xử lý ảnh, để tôi hiểu được tham số này điều khiển tần suất xử lý ảnh như thế nào.

#### Acceptance Criteria

1. THE Dialog SHALL hiển thị label "Chu kỳ xử lý ảnh (bội số của chu kỳ chụp)" cho trường passive_sample_spin
2. THE Dialog SHALL giữ nguyên chức năng của trường input này
3. THE Dialog SHALL duy trì giá trị mặc định và validation hiện tại

### Requirement 2: Ẩn Timeout Widget Cho READ_PASSIVE

**User Story:** Là người dùng, tôi muốn giao diện đơn giản hơn bằng cách ẩn các tùy chọn timeout không áp dụng cho "Đọc thụ động", để tôi có thể cấu hình action dễ dàng hơn.

#### Acceptance Criteria

1. WHEN người dùng chọn action "Đọc thụ động", THE Dialog SHALL ẩn timeout_widget (chứa "Thời gian tối đa chờ", "Chu kỳ kiểm tra", và "Timeout → làm tiếp bước sau")
2. WHEN người dùng chọn action khác (MOUSE_CLICK, IMAGE_DETECT), THE Dialog SHALL hiển thị timeout_widget như bình thường
3. THE Dialog SHALL duy trì layout gọn gàng sau khi ẩn timeout_widget
4. THE Dialog SHALL không hiển thị khoảng trống thừa từ timeout_widget đã ẩn

### Requirement 3: Cập Nhật Logic Xử Lý

**User Story:** Là nhà phát triển, tôi muốn logic code được cập nhật phù hợp với thay đổi UI, để đảm bảo chức năng hoạt động chính xác.

#### Acceptance Criteria

1. WHEN dialog được khởi tạo cho action "Đọc thụ động", THE System SHALL chỉ hiển thị các trường cần thiết
2. WHEN người dùng chuyển đổi giữa các loại action khác nhau, THE System SHALL hiển thị/ẩn các trường phù hợp
3. WHEN người dùng lưu cấu hình action "Đọc thụ động", THE System SHALL chỉ lưu các giá trị từ trường được hiển thị
4. THE System SHALL duy trì tương thích ngược với các cấu hình action "Đọc thụ động" đã tồn tại

### Requirement 4: Validation và Error Handling

**User Story:** Là người dùng, tôi muốn nhận được thông báo lỗi rõ ràng khi nhập sai thông tin, để tôi có thể sửa lỗi dễ dàng.

#### Acceptance Criteria

1. WHEN người dùng nhập giá trị không hợp lệ cho "Chu kỳ xử lý ảnh", THE System SHALL hiển thị thông báo lỗi cụ thể
2. WHEN người dùng để trống trường bắt buộc, THE System SHALL ngăn không cho lưu và hiển thị thông báo
3. THE System SHALL validate rằng chu kỳ xử lý ảnh phải là số nguyên dương
4. THE System SHALL validate rằng chu kỳ xử lý ảnh phải là bội số hợp lý của chu kỳ chụp