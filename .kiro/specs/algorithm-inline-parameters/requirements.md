# Requirements Document

## Introduction

Feature để thêm thuật toán threshold và hiển thị parameters của tất cả thuật toán ngay trong listview với khả năng edit inline, không cần mở dialog riêng.

## Glossary

- **Algorithm**: Thuật toán xử lý ảnh (preprocessing) như grayscale, upscale, contrast, threshold
- **Parameter**: Thông số có thể điều chỉnh của thuật toán (ví dụ: upscale factor, threshold value)
- **Inline_Editing**: Chỉnh sửa parameters trực tiếp trong listview mà không cần mở dialog
- **Multi_Image_Testing_Dialog**: Dialog để test nhiều window captures với các thuật toán khác nhau
- **Template_Matching**: Quá trình so sánh teaching image với window captures để tìm độ tương đồng

## Requirements

### Requirement 1: Thêm Thuật Toán Threshold

**User Story:** Là một user, tôi muốn có thuật toán threshold để xử lý ảnh text/chữ, để tôi có thể cải thiện độ chính xác template matching cho OCR.

#### Acceptance Criteria

1. WHEN user mở Multi-Image Algorithm Testing Dialog, THE System SHALL hiển thị thuật toán "Binary Threshold" trong dropdown
2. WHEN user chọn Binary Threshold algorithm, THE System SHALL áp dụng cv2.threshold với THRESH_BINARY
3. WHEN Binary Threshold được áp dụng, THE System SHALL chuyển ảnh thành binary (đen trắng) với threshold value
4. THE Binary_Threshold SHALL có parameters: threshold_value (0-255) và threshold_type (BINARY/BINARY_INV)

### Requirement 2: Hiển Thị Parameters Inline

**User Story:** Là một user, tôi muốn xem và chỉnh sửa parameters của thuật toán ngay trong list, để tôi không cần mở dialog riêng và có thể điều chỉnh nhanh chóng.

#### Acceptance Criteria

1. WHEN user add algorithm vào list, THE System SHALL hiển thị algorithm name và tất cả parameters bên dưới
2. WHEN algorithm có parameters, THE System SHALL tạo editable widgets (QSpinBox, QDoubleSpinBox) cho mỗi parameter
3. WHEN algorithm không có parameters, THE System SHALL chỉ hiển thị algorithm name
4. THE Parameter_Widgets SHALL được hiển thị với label và current value
5. THE List_Item_Height SHALL tự động điều chỉnh dựa trên số lượng parameters

### Requirement 3: Parameter Definitions cho Tất Cả Algorithms

**User Story:** Là một user, tôi muốn tùy chỉnh parameters của mọi thuật toán, để tôi có thể tối ưu hóa kết quả template matching cho từng trường hợp cụ thể.

#### Acceptance Criteria

1. THE Grayscale_Algorithm SHALL không có parameters (chỉ convert sang grayscale)
2. THE Upscale_Algorithm SHALL có parameter: scale_factor (1.0-5.0, default 2.0, step 0.1)
3. THE Contrast_Algorithm SHALL có parameter: contrast_level (0.5-3.0, default 1.5, step 0.1)
4. THE Sharpen_Algorithm SHALL có parameter: sharpen_strength (0.1-2.0, default 1.0, step 0.1)
5. THE Denoise_Algorithm SHALL có parameter: denoise_strength (1-10, default 5, step 1)
6. THE Binary_Threshold SHALL có parameters: threshold_value (0-255, default 127) và threshold_type (BINARY=0, BINARY_INV=1)
7. THE Full_Pipeline SHALL có tất cả parameters của các thuật toán thành phần

### Requirement 4: Real-time Parameter Updates

**User Story:** Là một user, tôi muốn thấy kết quả ngay khi thay đổi parameters, để tôi có thể điều chỉnh và xem preview real-time.

#### Acceptance Criteria

1. WHEN user thay đổi parameter value, THE System SHALL cập nhật algorithm config ngay lập tức
2. WHEN parameter được thay đổi, THE System SHALL refresh preview của window capture đang được chọn
3. WHEN user đang test algorithms, THE System SHALL sử dụng current parameter values
4. THE Parameter_Changes SHALL được lưu vào action khi user click OK

### Requirement 5: Parameter Validation

**User Story:** Là một user, tôi muốn system validate parameters, để tôi không thể nhập giá trị không hợp lệ và gây lỗi.

#### Acceptance Criteria

1. THE QSpinBox SHALL có minimum, maximum và step values được định nghĩa
2. THE QDoubleSpinBox SHALL có minimum, maximum, step và decimals được định nghĩa
3. WHEN user nhập giá trị ngoài range, THE System SHALL tự động clamp về giá trị hợp lệ
4. THE Parameter_Widgets SHALL hiển thị current value và cho phép edit bằng keyboard hoặc mouse

### Requirement 6: UI Layout Responsive

**User Story:** Là một user, tôi muốn UI tự động điều chỉnh khi có nhiều parameters, để interface luôn dễ sử dụng và không bị cắt xén.

#### Acceptance Criteria

1. WHEN algorithm có nhiều parameters, THE List_Item SHALL tự động tăng height
2. WHEN parameters được hiển thị, THE Layout SHALL sắp xếp parameters theo dạng grid hoặc vertical
3. THE Algorithm_List SHALL có scrollbar khi cần thiết
4. THE Parameter_Labels SHALL có minimum width để text không bị cắt

### Requirement 7: Backward Compatibility

**User Story:** Là một user, tôi muốn các tool và action hiện tại vẫn hoạt động bình thường, để không bị mất data hoặc functionality.

#### Acceptance Criteria

1. THE Existing_Actions SHALL load parameters từ saved config nếu có
2. WHEN action không có parameter config, THE System SHALL sử dụng default values
3. THE Tool_Manager SHALL save và load algorithm parameters trong JSON format
4. THE Old_Algorithm_Format SHALL vẫn được support (chỉ có config, không có parameters)

### Requirement 8: Testing Integration

**User Story:** Là một user, tôi muốn test algorithms với custom parameters, để tôi có thể so sánh hiệu quả của các setting khác nhau.

#### Acceptance Criteria

1. WHEN user click "Test Checked Images", THE System SHALL sử dụng current parameter values của algorithms trong list
2. WHEN test hoàn thành, THE Results SHALL hiển thị algorithm name và parameter values được sử dụng
3. THE Test_Results SHALL được lưu cùng với algorithm config để có thể reproduce
4. WHEN user thay đổi parameters sau khi test, THE System SHALL clear old results và yêu cầu test lại

## Input/Output

**Input:**
- User selections trong algorithm dropdown
- User parameter value changes trong inline widgets
- Window capture images để test
- Teaching image để so sánh

**Output:**
- Algorithm list với inline parameter widgets
- Real-time preview updates khi parameters thay đổi
- Test results với algorithm configs được sử dụng
- Saved action với algorithm parameters trong JSON

## Sơ đồ khối (Text-based)

```
┌─────────────────┐
│ Algorithm       │
│ Dropdown        │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Add Algorithm   │
│ to List         │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Create List     │
│ Item Widget     │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Add Parameter   │
│ Widgets Inline  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Connect Value   │
│ Change Signals  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Update Config   │
│ & Refresh       │
│ Preview         │
└─────────────────┘
```

## Technical Notes

- Sử dụng QSpinBox cho integer parameters (threshold_value, denoise_strength)
- Sử dụng QDoubleSpinBox cho float parameters (scale_factor, contrast_level, sharpen_strength)
- Parameters được lưu trong algorithm["config"] và algorithm["parameters"]
- Real-time updates thông qua signal/slot mechanism
- UI responsive bằng cách sử dụng dynamic layout và size hints
- Backward compatibility bằng cách check parameter existence trước khi access