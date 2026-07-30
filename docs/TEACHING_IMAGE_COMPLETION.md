# Teaching Image Feature - Hoàn thành

## Tổng quan
Đã hoàn thành việc di chuyển teaching image selection từ action config dialog vào các settings dialogs riêng biệt cho từng action type.

## Đã hoàn thành

### 1. MouseClickSettingsDialog ✅
**File:** `src/ui/mouse_click_settings_dialog.py`

**Thêm:**
- Group "Ảnh Teaching & Tọa độ Click"
- Label hiển thị đường dẫn ảnh
- Button "Tạo ảnh Teaching" / "Xem/Sửa ảnh Teaching"
- Button "Chọn file ảnh..."
- Spin boxes cho click coordinates (X, Y)

**Methods:**
- `_capture_teaching_image()`: Mở ImageCaptureDialog với click selection
- `_select_image_file()`: Chọn file ảnh từ file system
- `_update_image_button_text()`: Cập nhật text button dựa vào image_path

**Settings được save:**
- image_path
- click_x, click_y
- teaching_corner_x1/y1/x2/y2

### 2. ImageDetectSettingsDialog ✅
**File:** `src/ui/image_detect_settings_dialog.py`

**Thêm:**
- Group "Ảnh Teaching"
- Label hiển thị đường dẫn ảnh
- Button "Tạo ảnh Teaching" / "Xem/Sửa ảnh Teaching"
- Button "Chọn file ảnh..."

**Methods:**
- `_capture_teaching_image()`: Mở ImageCaptureDialog với `hide_click_selection=True`
- `_select_image_file()`: Chọn file ảnh từ file system
- `_update_image_button_text()`: Cập nhật text button dựa vào image_path

**Settings được save:**
- image_path
- teaching_corner_x1/y1/x2/y2

### 3. PassiveReadSettingsDialog ✅
**File:** `src/ui/passive_read_settings_dialog.py`

**Thêm:**
- Group "Ảnh Teaching"
- Label hiển thị đường dẫn ảnh
- Button "Tạo ảnh Teaching" / "Xem/Sửa ảnh Teaching"
- Button "Chọn file ảnh..."

**Methods:**
- `_capture_teaching_image()`: Mở ImageCaptureDialog với `hide_click_selection=True`
- `_select_image_file()`: Chọn file ảnh từ file system
- `_update_image_button_text()`: Cập nhật text button dựa vào image_path

**Settings được save:**
- image_path
- teaching_corner_x1/y1/x2/y2

### 4. ActionConfigDialog ✅
**File:** `src/ui/action_config_dialog.py`

**Thay đổi:**
- Xóa toàn bộ teaching image UI (image_btn, image_file_btn, image_path_label, coord_widget)
- Xóa methods: `capture_and_select_image()`, `select_image_file()`, `_has_teaching_image()`, `_update_teaching_button_text()`
- Xóa `on_action_type_changed()` method
- Giảm dialog height từ 600px xuống 250px
- Giảm file size từ 694 lines xuống 318 lines

**Cập nhật `_open_action_settings()`:**
- MOUSE_CLICK: Save image_path, click_x/y, teaching_corner_x1/y1/x2/y2
- IMAGE_DETECT: Save image_path, teaching_corner_x1/y1/x2/y2
- READ_PASSIVE: Save image_path, teaching_corner_x1/y1/x2/y2

### 5. Persistence ✅
**File:** `src/logic/tool_manager.py`

**Verified:**
- `_action_to_dict()`: Đã có tất cả teaching image fields
- `from_dict()`: Đã load tất cả teaching image fields
- Tất cả fields đều được save/load đúng

### 6. Data Model ✅
**File:** `src/logic/action_type.py`

**Verified:**
- AutoAction dataclass đã có tất cả fields:
  - image_path
  - click_x, click_y (cho MOUSE_CLICK)
  - teaching_corner_x1/y1/x2/y2

## Files thay đổi

1. `src/ui/action_config_dialog.py` - Xóa teaching image UI, giảm 376 lines
2. `src/ui/mouse_click_settings_dialog.py` - Thêm teaching image với click coords
3. `src/ui/image_detect_settings_dialog.py` - Thêm teaching image không có click coords
4. `src/ui/passive_read_settings_dialog.py` - Thêm teaching image không có click coords

## Commits

1. `[commit hash]` - Xóa teaching image UI từ ActionConfigDialog
2. `[commit hash]` - Thêm teaching image vào MouseClickSettingsDialog
3. `[commit hash]` - Thêm teaching image vào ImageDetectSettingsDialog
4. `[commit hash]` - Thêm teaching image vào PassiveReadSettingsDialog
5. `5ab31bf` - Thêm manual test plan cho teaching image feature

## Manual Test

Vui lòng test theo hướng dẫn tại: `docs/MANUAL_TEST_TEACHING_IMAGE.md`

**Test cases:**
1. MOUSE_CLICK - Teaching Image với Click Coordinates
2. IMAGE_DETECT - Teaching Image không có Click Coordinates
3. READ_PASSIVE - Teaching Image không có Click Coordinates
4. Chọn file ảnh từ file system
5. Xem/Sửa ảnh Teaching đã có
6. Kiểm tra persistence trong JSON

## Kiểm tra Persistence

**Checklist đã hoàn thành:**
- ✅ Add field to UI dialog
- ✅ Save to object in `get_settings()` method
- ✅ Load from object in `_load_settings()` method
- ✅ Verify field exists in `_action_to_dict()` in tool_manager.py
- ✅ Verify field exists in `from_dict()` in tool_manager.py
- ⏳ Test: Save → close app → reopen → verify data persists (cần user test)

## Lưu ý kỹ thuật

### Sự khác biệt giữa các action types:

**MOUSE_CLICK:**
- Có click coordinates (click_x, click_y)
- ImageCaptureDialog với click selection enabled
- Spin boxes để hiển thị/edit click coordinates

**IMAGE_DETECT & READ_PASSIVE:**
- Không có click coordinates
- ImageCaptureDialog với `hide_click_selection=True`
- Chỉ cần chọn vùng ảnh

### Teaching corners:
- teaching_corner_x1/y1: Top-left của ảnh teaching trên full window
- teaching_corner_x2/y2: Bottom-right của ảnh teaching trên full window
- Dùng để tự động tính Fixed ROI khi cần

### Button text logic:
- "Tạo ảnh Teaching": Khi chưa có ảnh hoặc file không tồn tại
- "Xem/Sửa ảnh Teaching": Khi đã có ảnh và file tồn tại

## Kết luận

Teaching image feature đã được di chuyển hoàn toàn vào các settings dialogs riêng biệt. Action config dialog giờ chỉ còn:
- Tên action
- Mục đích
- Loại hành động (dropdown)
- Button "⚙️ Cài đặt"

Tất cả settings chi tiết (bao gồm teaching image) được quản lý trong các settings dialogs chuyên biệt, giúp code dễ maintain và UI gọn gàng hơn.
