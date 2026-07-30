# Requirements Document

## Introduction

Feature cho phép người dùng cấu hình preprocessing algorithms cho template matching và OCR từ settings dialogs. User có thể xem danh sách algorithms đang áp dụng và mở Multi-Image Algorithm Testing Dialog để configure.

## Glossary

- **Template_Matching_Algorithms**: Danh sách thuật toán tiền xử lý cho IMAGE_DETECT và MOUSE_CLICK actions
- **OCR_Algorithms**: Danh sách thuật toán tiền xử lý cho READ_PASSIVE OCR mode
- **Algorithm_ListView**: ListView read-only hiển thị algorithms với parameters
- **Multi_Image_Testing_Dialog**: Dialog hiện tại để test và configure algorithms
- **Settings_Dialog**: Image Detect Settings Dialog và Passive Read Settings Dialog

## Requirements

### Requirement 1: Template Matching Algorithms UI

**User Story:** Là một user, tôi muốn xem và cấu hình preprocessing algorithms cho template matching, để cải thiện độ chính xác nhận diện ảnh.

#### Acceptance Criteria

1. WHEN user mở Image Detect Settings Dialog, THE Settings_Dialog SHALL hiển thị Template Matching Preprocessing section
2. THE Algorithm_ListView SHALL hiển thị danh sách Template_Matching_Algorithms với parameters
3. WHEN chưa có algorithms, THE Algorithm_ListView SHALL hiển thị "Không có thuật toán"
4. WHEN user click "Cấu hình Template Matching Algorithms" button, THE Settings_Dialog SHALL mở Multi_Image_Testing_Dialog
5. WHEN user apply algorithms từ Multi_Image_Testing_Dialog, THE Template_Matching_Algorithms SHALL được cập nhật

### Requirement 2: OCR Algorithms UI

**User Story:** Là một user, tôi muốn xem và cấu hình preprocessing algorithms cho OCR, để cải thiện chất lượng đọc text.

#### Acceptance Criteria

1. WHEN user mở Passive Read Settings Dialog với mode "Đọc dữ liệu", THE Settings_Dialog SHALL hiển thị OCR Preprocessing section
2. THE Algorithm_ListView SHALL hiển thị danh sách OCR_Algorithms với parameters
3. WHEN chưa có algorithms, THE Algorithm_ListView SHALL hiển thị "Không có thuật toán"
4. WHEN user click "Cấu hình OCR Algorithms" button, THE Settings_Dialog SHALL mở Multi_Image_Testing_Dialog
5. WHEN user apply algorithms từ Multi_Image_Testing_Dialog, THE OCR_Algorithms SHALL được cập nhật

### Requirement 3: Algorithm Display Format

**User Story:** Là một user, tôi muốn xem chi tiết từng algorithm và parameters, để hiểu rõ cấu hình hiện tại.

#### Acceptance Criteria

1. THE Algorithm_ListView SHALL hiển thị từng algorithm trên một dòng riêng
2. WHEN algorithm có parameters, THE Algorithm_ListView SHALL hiển thị format "Algorithm_Name (param1: value1, param2: value2)"
3. WHEN algorithm không có parameters, THE Algorithm_ListView SHALL hiển thị chỉ "Algorithm_Name"
4. THE Algorithm_ListView SHALL sắp xếp algorithms theo thứ tự áp dụng
5. THE Algorithm_ListView SHALL có scroll bar khi danh sách dài

### Requirement 4: Multi-Image Testing Dialog Integration

**User Story:** Là một user, tôi muốn apply algorithms từ Multi-Image Testing Dialog về settings dialogs, để sử dụng cấu hình đã test.

#### Acceptance Criteria

1. THE Multi_Image_Testing_Dialog SHALL có button "Apply to Template Matching"
2. THE Multi_Image_Testing_Dialog SHALL có button "Apply to OCR Mode"
3. WHEN user click "Apply to Template Matching", THE Template_Matching_Algorithms SHALL được save vào action
4. WHEN user click "Apply to OCR Mode", THE OCR_Algorithms SHALL được save vào action
5. WHEN apply thành công, THE Multi_Image_Testing_Dialog SHALL hiển thị thông báo xác nhận

### Requirement 5: Data Persistence

**User Story:** Là một user, tôi muốn algorithms configuration được lưu trữ, để không mất cấu hình khi đóng mở app.

#### Acceptance Criteria

1. THE Template_Matching_Algorithms SHALL được lưu vào AutoAction.template_matching_algorithms field
2. THE OCR_Algorithms SHALL được lưu vào AutoAction.ocr_algorithms field
3. WHEN save tool, THE algorithms configurations SHALL được serialize vào JSON
4. WHEN load tool, THE algorithms configurations SHALL được deserialize từ JSON
5. THE algorithms configurations SHALL tương thích với existing preprocessing_config field

### Requirement 6: Algorithm Format Compatibility

**User Story:** Là một developer, tôi muốn algorithm format tương thích với Multi-Image Testing Dialog, để đảm bảo data consistency.

#### Acceptance Criteria

1. THE Template_Matching_Algorithms format SHALL tương thích với Multi_Image_Testing_Dialog algorithms format
2. THE OCR_Algorithms format SHALL tương thích với Multi_Image_Testing_Dialog algorithms format
3. WHEN convert algorithms từ Multi_Image_Testing_Dialog, THE format SHALL được preserve
4. THE algorithm parameters SHALL được validate trước khi save
5. WHEN algorithm format invalid, THE system SHALL hiển thị error message

### Requirement 7: UI Layout Integration

**User Story:** Là một user, tôi muốn preprocessing sections được tích hợp tự nhiên vào settings dialogs, để không làm phức tạp UI.

#### Acceptance Criteria

1. THE Template Matching Preprocessing section SHALL được đặt sau Teaching Image section trong Image Detect Settings Dialog
2. THE OCR Preprocessing section SHALL được đặt trong left column của Passive Read Settings Dialog
3. THE Algorithm_ListView SHALL có height tối đa 120px với scroll bar
4. THE "Cấu hình" buttons SHALL có icon và text rõ ràng
5. THE sections SHALL có GroupBox với title phù hợp
