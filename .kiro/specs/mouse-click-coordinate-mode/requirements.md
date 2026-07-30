# Requirements Document

## Introduction

Feature bổ sung chế độ click chuột theo tọa độ cố định trên window game cho action MOUSE_CLICK. Giải quyết vấn đề khi đối tượng nhận diện bị che, không thể dùng template matching.

## Glossary

- **Click_Mode**: Chế độ click chuột (image-based hoặc coordinate-based)
- **Client_Coordinates**: Tọa độ trong client area của window game (không tính title bar, border)
- **Template_Matching**: Nhận diện ảnh để tìm vị trí click
- **Teaching_Dialog**: Dialog để chụp ảnh và chọn điểm click

## Requirements

### Requirement 1: Data Model

**User Story:** Là developer, tôi muốn có fields mới trong AutoAction để lưu trữ thông tin chế độ click theo tọa độ.

#### Acceptance Criteria

1. THE AutoAction SHALL have field `click_by_coordinate` (bool, default False)
2. THE AutoAction SHALL have field `screen_click_x` (int, tọa độ client X)
3. THE AutoAction SHALL have field `screen_click_y` (int, tọa độ client Y)

### Requirement 2: Persistence

**User Story:** Là user, tôi muốn settings được lưu và load đúng khi đóng/mở app.

#### Acceptance Criteria

1. WHEN saving action to JSON, THE Tool_Manager SHALL include `click_by_coordinate`, `screen_click_x`, `screen_click_y`
2. WHEN loading action from JSON, THE Tool_Manager SHALL restore `click_by_coordinate`, `screen_click_x`, `screen_click_y`
3. WHEN `click_by_coordinate` is missing in JSON, THE Tool_Manager SHALL default to False

### Requirement 3: UI - Chế độ Click

**User Story:** Là user, tôi muốn có dropdown để chọn chế độ click trong dialog settings.

#### Acceptance Criteria

1. THE Mouse_Click_Settings_Dialog SHALL have dropdown "Chế độ click" với 2 options: "Click theo hình ảnh", "Click theo tọa độ"
2. WHEN dropdown value changes, THE Dialog SHALL show/hide relevant layouts
3. THE Dialog SHALL display common layouts (Thời gian chờ, Tùy chọn click, Nhảy về step) at top, always visible

### Requirement 4: UI - Layouts cho chế độ hình ảnh

**User Story:** Là user, khi chọn chế độ "Click theo hình ảnh", tôi muốn thấy các settings liên quan.

#### Acceptance Criteria

1. WHEN mode is "Click theo hình ảnh", THE Dialog SHALL show layouts: Nhận diện ảnh, Ảnh Teaching Tọa độ Click
2. WHEN mode is "Click theo tọa độ", THE Dialog SHALL hide these layouts

### Requirement 5: UI - Layout cho chế độ tọa độ

**User Story:** Là user, khi chọn chế độ "Click theo tọa độ", tôi muốn có layout để teaching điểm click.

#### Acceptance Criteria

1. WHEN mode is "Click theo tọa độ", THE Dialog SHALL show layout "Teaching điểm click"
2. THE Layout SHALL have button to open Teaching_Dialog
3. THE Layout SHALL display current click coordinates (screen_click_x, screen_click_y)
4. WHEN mode is "Click theo hình ảnh", THE Dialog SHALL hide this layout

### Requirement 6: Teaching Dialog - Disable Region Selection

**User Story:** Là user, khi teaching cho chế độ tọa độ, tôi chỉ cần chọn điểm click, không cần chọn vùng.

#### Acceptance Criteria

1. THE Image_Capture_Dialog SHALL accept parameter `hide_region_selection` (bool)
2. WHEN `hide_region_selection` is True, THE Dialog SHALL disable/hide button "Chọn vùng"
3. WHEN opening Teaching_Dialog for coordinate mode, THE Dialog SHALL pass `hide_region_selection=True`

### Requirement 7: Teaching Dialog - Restore Click Point

**User Story:** Là user, khi mở lại dialog teaching, tôi muốn thấy điểm click đã chọn trước đó.

#### Acceptance Criteria

1. WHEN opening Teaching_Dialog with existing `screen_click_x`, `screen_click_y`, THE Dialog SHALL display click point marker
2. THE Click point marker SHALL be visible at correct position on captured image

### Requirement 8: Resource Cleanup

**User Story:** Là user, khi thay đổi chế độ click, tôi muốn resources cũ được xóa.

#### Acceptance Criteria

1. WHEN changing from "Click theo hình ảnh" to "Click theo tọa độ", THE Dialog SHALL clear image_path, click_x, click_y
2. WHEN changing from "Click theo tọa độ" to "Click theo hình ảnh", THE Dialog SHALL clear screen_click_x, screen_click_y
3. IF image file exists, THE Dialog SHALL delete the old image file

### Requirement 9: Runtime Execution

**User Story:** Là user, tôi muốn action click chuột hoạt động đúng theo chế độ đã chọn.

#### Acceptance Criteria

1. WHEN `click_by_coordinate` is True, THE System_Executor SHALL click directly at (screen_click_x, screen_click_y) in client coordinates
2. WHEN `click_by_coordinate` is False, THE System_Executor SHALL use template matching (current behavior)
3. WHEN `click_by_coordinate` is True and coordinates are invalid, THE System_Executor SHALL log error and return False
