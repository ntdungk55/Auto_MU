# Template Mask Regions Feature - Completion Summary

## Tổng quan
Feature cho phép user vẽ mask regions trên teaching image để bỏ qua vùng text động khi template matching, giúp tăng độ chính xác khi chỉ có text thay đổi mà layout không đổi.

## Đã hoàn thành

### 1. Data Model (action_type.py)
- ✅ Thêm field `mask_regions: list[dict]` vào AutoAction
- ✅ Format: `[{"x": int, "y": int, "w": int, "h": int}, ...]`

### 2. Persistence (tool_manager.py)
- ✅ Save mask_regions trong `_action_to_dict()`
- ✅ Load mask_regions trong `from_dict()`
- ✅ Backward compatible: empty list nếu không có

### 3. Template Matching Logic (system_executor.py)
- ✅ Thêm method `_create_mask_array()` để tạo mask từ regions
- ✅ Update `find_image_in_window_with_score_adaptive()` để hỗ trợ mask
- ✅ Scale mask theo scale của template
- ✅ Dùng `cv2.matchTemplate(..., mask=mask)` khi có mask
- ✅ Handle empty case: None/[] → matching bình thường
- ✅ Update tất cả nơi gọi matching để truyền mask_regions

### 4. UI (image_capture_dialog.py)
- ✅ Thêm buttons "Vẽ Mask" và "Xóa tất cả mask"
- ✅ Vẽ nhiều mask rectangles (màu đỏ, alpha=0.3)
- ✅ Click để select mask (viền dày 3px)
- ✅ Delete key để xóa mask đã select
- ✅ Right-click menu "Xóa mask"
- ✅ Validation: mask không được > 90% ảnh
- ✅ Methods: `toggle_mask_drawing()`, `add_mask_rect()`, `select_mask_at_pos()`, `delete_selected_mask()`, `get_mask_regions()`, `validate_mask_regions()`

### 5. Settings Dialogs
- ✅ Update `image_detect_settings_dialog.py` để save mask_regions
- ✅ Update `mouse_click_settings_dialog.py` để save mask_regions

### 6. Tests
- ✅ Unit tests: `tests/test_mask_regions.py`
  - test_mask_regions_field_exists
  - test_mask_regions_save_load
  - test_create_mask_array
  - test_template_matching_with_mask
  - test_mask_regions_validation
- ✅ Manual test plan: `docs/MANUAL_TEST_MASK_REGIONS.md`

## Files thay đổi

| File | Thay đổi | Dòng |
|------|----------|------|
| `src/logic/action_type.py` | Thêm mask_regions field | +4 |
| `src/logic/tool_manager.py` | Save/load mask_regions | +4 |
| `src/logic/system_executor/system_executor.py` | Create mask, matching logic | +80 |
| `src/ui/image_capture_dialog.py` | UI vẽ mask, select, delete | +200 |
| `src/ui/image_detect_settings_dialog.py` | Save mask_regions | +2 |
| `src/ui/mouse_click_settings_dialog.py` | Save mask_regions | +2 |
| `tests/test_mask_regions.py` | Unit tests | +170 |
| `docs/MANUAL_TEST_MASK_REGIONS.md` | Manual test plan | +200 |
| `.kiro/specs/template-mask-regions/requirements.md` | Requirements doc | +150 |

**Tổng:** ~812 dòng code mới

## Cách sử dụng

1. Mở tool editor → chọn action IMAGE_DETECT hoặc MOUSE_CLICK
2. Click "⚙️ Cài đặt" → "Tạo ảnh Teaching"
3. Chụp ảnh và crop vùng cần thiết
4. **Click "Vẽ Mask"** → vẽ hình chữ nhật bao quanh vùng text động
5. Vẽ nhiều mask nếu cần
6. Click vào mask để select → Delete key hoặc chuột phải để xóa
7. Click "OK" → mask regions được lưu vào action

## Kết quả

- Template matching với mask có score cao hơn khi text thay đổi
- Threshold cao (0.8) vẫn match được khi chỉ text thay đổi
- Backward compatible: tool cũ vẫn chạy bình thường

## Manual Test

Vui lòng test theo hướng dẫn tại: `docs/MANUAL_TEST_MASK_REGIONS.md`

## Commit

Commit: b41b966
Branch: refactor/clean-architecture
Message: [Feature] Template Mask Regions - Ignore dynamic text when matching
