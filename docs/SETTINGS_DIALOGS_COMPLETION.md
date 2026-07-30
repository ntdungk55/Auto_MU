# Settings Dialogs - Hoàn thành các fields còn thiếu

## Tổng quan
Đã thêm đầy đủ 9 fields còn thiếu vào các settings dialogs để đảm bảo tất cả dữ liệu được lưu/load đúng.

## Các fields đã thêm

### 1. MouseClickSettingsDialog
**Thêm 3 fields:**
- `multiscale_min` (float, default: 0.70) - Khoảng scale tối thiểu
- `multiscale_max` (float, default: 1.30) - Khoảng scale tối đa
- `multiscale_step` (float, default: 0.05) - Bước nhảy scale

**UI:**
- Thêm 3 spinbox cho min/max/step
- Ẩn/hiện khi checkbox multiscale được bật/tắt
- Method `_on_multiscale_changed()` để control visibility

### 2. ImageDetectSettingsDialog
**Thêm 9 fields:**

**Multiscale (3 fields):**
- `multiscale_min` (float, default: 0.70)
- `multiscale_max` (float, default: 1.30)
- `multiscale_step` (float, default: 0.05)

**Telegram notification (1 field):**
- `notification_dedup_minutes` (int, default: 1) - Thời gian dedup để tránh spam

**OCR preprocessing (5 fields):**
- `ocr_upscale_enabled` (bool, default: True) - Bật phóng to ảnh
- `ocr_upscale_factor` (float, default: 2.0) - Hệ số phóng to (1.0-5.0)
- `ocr_enhance_contrast` (bool, default: True) - Tăng độ tương phản (CLAHE)
- `ocr_sharpen` (bool, default: True) - Làm sắc nét (Unsharp Mask)
- `ocr_denoise` (bool, default: False) - Khử nhiễu (Bilateral Filter - chậm)

**UI:**
- Multiscale range widgets (giống MouseClickSettingsDialog)
- Dedup minutes spinbox trong Telegram group
- 5 checkboxes + 1 spinbox cho OCR preprocessing
- Method `_on_ocr_upscale_changed()` để ẩn/hiện upscale factor

### 3. PassiveReadSettingsDialog
**Thêm 6 fields:**

**Telegram notification (1 field):**
- `notification_dedup_minutes` (int, default: 1)

**OCR preprocessing (5 fields):**
- `ocr_upscale_enabled` (bool, default: True)
- `ocr_upscale_factor` (float, default: 2.0)
- `ocr_enhance_contrast` (bool, default: True)
- `ocr_sharpen` (bool, default: True)
- `ocr_denoise` (bool, default: False)

**UI:**
- Giống ImageDetectSettingsDialog
- Dedup minutes spinbox
- OCR preprocessing options với checkboxes

## Cập nhật _open_action_settings()

Đã cập nhật method `_open_action_settings()` trong `action_config_dialog.py` để lưu tất cả fields mới:

### MOUSE_CLICK
```python
self.action.multiscale_min = settings["multiscale_min"]
self.action.multiscale_max = settings["multiscale_max"]
self.action.multiscale_step = settings["multiscale_step"]
```

### IMAGE_DETECT
```python
# Multiscale
self.action.multiscale_min = settings["multiscale_min"]
self.action.multiscale_max = settings["multiscale_max"]
self.action.multiscale_step = settings["multiscale_step"]

# OCR preprocessing
self.action.ocr_upscale_enabled = settings["ocr_upscale_enabled"]
self.action.ocr_upscale_factor = settings["ocr_upscale_factor"]
self.action.ocr_enhance_contrast = settings["ocr_enhance_contrast"]
self.action.ocr_sharpen = settings["ocr_sharpen"]
self.action.ocr_denoise = settings["ocr_denoise"]

# Telegram
self.action.notification_dedup_minutes = settings["notification_dedup_minutes"]
```

### READ_PASSIVE
```python
# OCR preprocessing
self.action.ocr_upscale_enabled = settings["ocr_upscale_enabled"]
self.action.ocr_upscale_factor = settings["ocr_upscale_factor"]
self.action.ocr_enhance_contrast = settings["ocr_enhance_contrast"]
self.action.ocr_sharpen = settings["ocr_sharpen"]
self.action.ocr_denoise = settings["ocr_denoise"]

# Telegram
self.action.notification_dedup_minutes = settings["notification_dedup_minutes"]
```

## Kiểm tra hoàn chỉnh

### Checklist fields theo tool_manager.py
✅ Tất cả 9 fields đã được thêm vào đúng dialogs:
- ✅ multiscale_min (MouseClick, ImageDetect)
- ✅ multiscale_max (MouseClick, ImageDetect)
- ✅ multiscale_step (MouseClick, ImageDetect)
- ✅ notification_dedup_minutes (ImageDetect, PassiveRead)
- ✅ ocr_upscale_enabled (ImageDetect, PassiveRead)
- ✅ ocr_upscale_factor (ImageDetect, PassiveRead)
- ✅ ocr_enhance_contrast (ImageDetect, PassiveRead)
- ✅ ocr_sharpen (ImageDetect, PassiveRead)
- ✅ ocr_denoise (ImageDetect, PassiveRead)

### Diagnostics
✅ Không có lỗi Python trong tất cả 4 files:
- action_config_dialog.py
- mouse_click_settings_dialog.py
- image_detect_settings_dialog.py
- passive_read_settings_dialog.py

## Bước tiếp theo

**CHƯA HOÀN THÀNH:**
Main dialog (`action_config_dialog.py`) vẫn còn tất cả old UI widgets (chỉ ẩn bằng setVisible(False), chưa xóa).

**Cần làm:**
Xóa hết old UI widgets khỏi main dialog để code sạch hơn và dễ maintain.

## Commit
```
Commit: 1260e45
Message: Thêm các fields còn thiếu vào settings dialogs
```
