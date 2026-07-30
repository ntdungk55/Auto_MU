# Requirements Document

## Introduction

Refactor action configuration dialog để tách các settings phức tạp ra thành dialog riêng cho từng loại action. Hiện tại dialog quá dài và khó quản lý khi có nhiều settings cho mỗi action type.

## Glossary

- **Action**: Một bước thực thi trong tool (KEYBOARD, MOUSE_CLICK, IMAGE_DETECT, READ_PASSIVE)
- **Action Settings Dialog**: Dialog riêng chứa các settings nâng cao cho từng loại action
- **Main Action Dialog**: Dialog chính để cấu hình action (tên, mục đích, loại action)
- **Settings Button**: Nút "Cài đặt" để mở dialog settings tương ứng với action type

## Requirements

### Requirement 1: Tạo nút Settings cho mỗi Action Type

**User Story:** Là người dùng, tôi muốn có nút "Cài đặt" riêng cho mỗi loại action, để tôi có thể cấu hình các settings nâng cao một cách dễ dàng.

#### Acceptance Criteria

1. WHEN người dùng chọn action type, THE System SHALL hiển thị nút "⚙️ Cài đặt" bên cạnh dropdown action type
2. WHEN người dùng click nút "Cài đặt", THE System SHALL mở dialog settings tương ứng với action type đã chọn
3. THE System SHALL hiển thị nút "Cài đặt" cho tất cả action types (KEYBOARD, MOUSE_CLICK, IMAGE_DETECT, READ_PASSIVE)

### Requirement 2: Tạo Dialog Settings cho KEYBOARD

**User Story:** Là người dùng, tôi muốn cấu hình settings cho KEYBOARD trong dialog riêng, để tôi có thể chọn phím và cấu hình delay.

#### Acceptance Criteria

1. THE System SHALL tạo file `src/ui/keyboard_settings_dialog.py`
2. THE Dialog SHALL chứa: key input (dropdown + autocomplete), delay settings
3. WHEN người dùng lưu settings, THE System SHALL cập nhật vào action object
4. WHEN người dùng mở dialog, THE System SHALL load settings hiện tại từ action object

### Requirement 3: Tạo Dialog Settings cho MOUSE_CLICK

**User Story:** Là người dùng, tôi muốn cấu hình settings cho MOUSE_CLICK trong dialog riêng, để tôi có thể tập trung vào các tùy chọn liên quan.

#### Acceptance Criteria

1. THE System SHALL tạo file `src/ui/mouse_click_settings_dialog.py`
2. THE Dialog SHALL chứa các settings: threshold, multiscale, alt_click, timeout, check_interval, continue_on_timeout, delay
3. WHEN người dùng lưu settings, THE System SHALL cập nhật vào action object
4. WHEN người dùng mở dialog, THE System SHALL load settings hiện tại từ action object

### Requirement 4: Tạo Dialog Settings cho IMAGE_DETECT

**User Story:** Là người dùng, tôi muốn cấu hình settings cho IMAGE_DETECT trong dialog riêng, để tôi có thể quản lý OCR và Gemini settings dễ dàng.

#### Acceptance Criteria

1. THE System SHALL tạo file `src/ui/image_detect_settings_dialog.py`
2. THE Dialog SHALL chứa các settings: threshold, multiscale, timeout, check_interval, continue_on_timeout, delay, read_data, OCR settings, Gemini settings, Telegram notification
3. WHEN read_data được bật, THE System SHALL hiển thị OCR và Gemini settings
4. WHEN Gemini được bật, THE System SHALL hiển thị Telegram notification settings

### Requirement 5: Tạo Dialog Settings cho READ_PASSIVE

**User Story:** Là người dùng, tôi muốn cấu hình settings cho READ_PASSIVE trong dialog riêng, để tôi có thể quản lý passive reading settings và Fixed ROI.

#### Acceptance Criteria

1. THE System SHALL tạo file `src/ui/passive_read_settings_dialog.py`
2. THE Dialog SHALL chứa các settings: passive_sample_every, passive_only_new_frame, passive_cancel_old, passive_keywords, Fixed ROI, OCR settings, Gemini settings, Telegram notification
3. WHEN Fixed ROI được bật, THE System SHALL hiển thị ROI coordinates
4. WHEN Gemini được bật, THE System SHALL hiển thị Telegram notification settings

### Requirement 6: Đơn giản hóa Main Action Dialog

**User Story:** Là người dùng, tôi muốn main action dialog ngắn gọn hơn, để tôi có thể tập trung vào thông tin cơ bản của action.

#### Acceptance Criteria

1. THE Main Dialog SHALL chỉ chứa: tên, mục đích, action type, nút "⚙️ Cài đặt", goto_step
2. THE Main Dialog SHALL có nút "⚙️ Cài đặt" để mở settings dialog tương ứng
3. THE Main Dialog SHALL giữ nguyên chức năng chọn/tạo teaching image (cho MOUSE_CLICK, IMAGE_DETECT, READ_PASSIVE)
4. THE Main Dialog SHALL có chiều cao cố định ~400px (thay vì 600px hiện tại)

### Requirement 7: Backward Compatibility

**User Story:** Là developer, tôi muốn đảm bảo code cũ vẫn hoạt động, để không phá vỡ các tool đã tạo.

#### Acceptance Criteria

1. THE System SHALL giữ nguyên tất cả các trường trong AutoAction dataclass
2. THE System SHALL load/save settings từ JSON file như cũ
3. THE System SHALL không thay đổi logic lưu/load tool
4. THE System SHALL chỉ thay đổi UI, không thay đổi data structure
