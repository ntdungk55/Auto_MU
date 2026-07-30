# PassiveReadSettingsDialog Screenshot Capture Bug Fix

## Vấn đề

**Lỗi:** `'int' object has no attribute 'target_window_hwnd'`

**Khi nào xảy ra:** Khi user click button "Tạo ảnh Teaching" trong PassiveReadSettingsDialog

**Nguyên nhân:** 
- Code đang cố truy cập `parent_dialog.target_window_hwnd`
- Nhưng `PassiveReadSettingsDialog` đã nhận `target_window_hwnd` qua constructor
- Parent dialog (`ActionConfigDialog`) không có attribute `target_window_hwnd`

## Giải pháp

**File:** `src/ui/passive_read_settings_dialog.py`

**Thay đổi trong method `_capture_teaching_image()`:**

```python
# CŨ (BUG):
parent_dialog = self.parent()
if not hasattr(parent_dialog, 'target_window_hwnd') or not parent_dialog.target_window_hwnd:
    QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
    return

dialog = ImageCaptureDialog(
    parent_dialog.target_window_hwnd,
    parent=self,
    tool_id=getattr(parent_dialog, "tool_id", None),
    ...
)

# MỚI (FIXED):
if not self.target_window_hwnd:
    QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
    return

dialog = ImageCaptureDialog(
    self.target_window_hwnd,
    parent=self,
    tool_id=self.tool_id,
    ...
)
```

**Lý do:**
- `PassiveReadSettingsDialog.__init__()` đã nhận `target_window_hwnd` và `tool_id` qua parameters
- Nên dùng `self.target_window_hwnd` và `self.tool_id` thay vì lấy từ parent

## Testing

**Manual Test:**
1. Mở tool editor
2. Tạo action READ_PASSIVE
3. Click "Cài đặt chi tiết"
4. Click "Tạo ảnh Teaching"
5. Verify: Dialog chụp ảnh mở thành công, không có lỗi

**Kết quả:** ✅ Fix thành công, không còn lỗi

## Commit

**Commit hash:** a0e9465

**Commit message:** `[Fix] PassiveReadSettingsDialog - Fix screenshot capture window handle error`

## Files thay đổi

- `src/ui/passive_read_settings_dialog.py`: Fix method `_capture_teaching_image()`

## Tác động

- **Backward compatible:** 100% (chỉ fix bug, không thay đổi behavior)
- **Breaking changes:** Không có
- **Rủi ro:** Rất thấp (fix đơn giản, logic rõ ràng)
