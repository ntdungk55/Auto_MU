# Manual Test Plan: Teaching Image trong Settings Dialogs

## Mục đích
Kiểm tra việc load và save teaching image trong các settings dialogs (MOUSE_CLICK, IMAGE_DETECT, READ_PASSIVE)

## Test Case 1: MOUSE_CLICK - Teaching Image với Click Coordinates

**Điều kiện tiên quyết:**
- App đang chạy
- Đã chọn window game
- Có tool với action MOUSE_CLICK

**Các bước thực hiện:**
1. Mở tool editor
2. Chọn một action MOUSE_CLICK (hoặc tạo mới)
3. Click "⚙️ Cài đặt" để mở MouseClickSettingsDialog
4. Trong group "Ảnh Teaching & Tọa độ Click":
   - Click "Tạo ảnh Teaching"
   - Chọn vùng ảnh và điểm click
   - Verify: Label hiển thị "Đã chọn: [tên file]"
   - Verify: Button đổi thành "Xem/Sửa ảnh Teaching"
5. Click "Lưu" để đóng settings dialog
6. Click "OK" để lưu action
7. Click "Lưu Tool" để save tool
8. **Đóng app hoàn toàn**
9. **Mở lại app**
10. Mở lại tool vừa save
11. Chọn action MOUSE_CLICK vừa tạo
12. Click "⚙️ Cài đặt"

**Kết quả mong đợi:**
- Label hiển thị "Đã chọn: [tên file]" (đúng tên file đã chọn)
- Button hiển thị "Xem/Sửa ảnh Teaching"
- Click coordinates (X, Y) được load đúng
- File ảnh vẫn tồn tại trong thư mục images/

**Cài đặt cần kiểm tra:**
- image_path: Đường dẫn file ảnh
- click_x: Tọa độ X
- click_y: Tọa độ Y
- teaching_corner_x1/y1/x2/y2: Tọa độ góc ảnh teaching

---

## Test Case 2: IMAGE_DETECT - Teaching Image không có Click Coordinates

**Điều kiện tiên quyết:**
- App đang chạy
- Đã chọn window game
- Có tool với action IMAGE_DETECT

**Các bước thực hiện:**
1. Mở tool editor
2. Chọn một action IMAGE_DETECT (hoặc tạo mới)
3. Click "⚙️ Cài đặt" để mở ImageDetectSettingsDialog
4. Trong group "Ảnh Teaching":
   - Click "Tạo ảnh Teaching"
   - Chọn vùng ảnh (KHÔNG có điểm click vì IMAGE_DETECT không cần)
   - Verify: Label hiển thị "Đã chọn: [tên file]"
   - Verify: Button đổi thành "Xem/Sửa ảnh Teaching"
5. Click "Lưu" để đóng settings dialog
6. Click "OK" để lưu action
7. Click "Lưu Tool" để save tool
8. **Đóng app hoàn toàn**
9. **Mở lại app**
10. Mở lại tool vừa save
11. Chọn action IMAGE_DETECT vừa tạo
12. Click "⚙️ Cài đặt"

**Kết quả mong đợi:**
- Label hiển thị "Đã chọn: [tên file]" (đúng tên file đã chọn)
- Button hiển thị "Xem/Sửa ảnh Teaching"
- File ảnh vẫn tồn tại trong thư mục images/

**Cài đặt cần kiểm tra:**
- image_path: Đường dẫn file ảnh
- teaching_corner_x1/y1/x2/y2: Tọa độ góc ảnh teaching

---

## Test Case 3: READ_PASSIVE - Teaching Image không có Click Coordinates

**Điều kiện tiên quyết:**
- App đang chạy
- Đã chọn window game
- Có tool với action READ_PASSIVE

**Các bước thực hiện:**
1. Mở tool editor
2. Chọn một action READ_PASSIVE (hoặc tạo mới)
3. Click "⚙️ Cài đặt" để mở PassiveReadSettingsDialog
4. Trong group "Ảnh Teaching":
   - Click "Tạo ảnh Teaching"
   - Chọn vùng ảnh (KHÔNG có điểm click vì READ_PASSIVE không cần)
   - Verify: Label hiển thị "Đã chọn: [tên file]"
   - Verify: Button đổi thành "Xem/Sửa ảnh Teaching"
5. Click "Lưu" để đóng settings dialog
6. Click "OK" để lưu action
7. Click "Lưu Tool" để save tool
8. **Đóng app hoàn toàn**
9. **Mở lại app**
10. Mở lại tool vừa save
11. Chọn action READ_PASSIVE vừa tạo
12. Click "⚙️ Cài đặt"

**Kết quả mong đợi:**
- Label hiển thị "Đã chọn: [tên file]" (đúng tên file đã chọn)
- Button hiển thị "Xem/Sửa ảnh Teaching"
- File ảnh vẫn tồn tại trong thư mục images/

**Cài đặt cần kiểm tra:**
- image_path: Đường dẫn file ảnh
- teaching_corner_x1/y1/x2/y2: Tọa độ góc ảnh teaching

---

## Test Case 4: Chọn file ảnh từ file system

**Điều kiện tiên quyết:**
- App đang chạy
- Có file ảnh sẵn trên máy (.png, .jpg, .jpeg, .bmp)

**Các bước thực hiện:**
1. Mở tool editor
2. Chọn một action bất kỳ (MOUSE_CLICK, IMAGE_DETECT, hoặc READ_PASSIVE)
3. Click "⚙️ Cài đặt"
4. Click "Chọn file ảnh..."
5. Chọn file ảnh từ file system
6. Verify: File được copy vào thư mục images/[tool_name]/
7. Verify: Label hiển thị "Đã chọn: [tên file]"
8. Click "Lưu" và save tool
9. **Đóng app hoàn toàn**
10. **Mở lại app**
11. Mở lại tool và action
12. Click "⚙️ Cài đặt"

**Kết quả mong đợi:**
- Label hiển thị đúng tên file
- File ảnh vẫn tồn tại trong thư mục images/[tool_name]/
- Button hiển thị "Xem/Sửa ảnh Teaching"

---

## Test Case 5: Xem/Sửa ảnh Teaching đã có

**Điều kiện tiên quyết:**
- Đã có action với teaching image

**Các bước thực hiện:**
1. Mở tool editor
2. Chọn action đã có teaching image
3. Click "⚙️ Cài đặt"
4. Verify: Button hiển thị "Xem/Sửa ảnh Teaching"
5. Click "Xem/Sửa ảnh Teaching"
6. Verify: ImageCaptureDialog mở ra với ảnh cũ
7. Chọn vùng mới (hoặc giữ nguyên)
8. Click OK
9. Verify: Label cập nhật tên file mới (nếu có thay đổi)

**Kết quả mong đợi:**
- Dialog mở ra với ảnh cũ được load
- Có thể chọn vùng mới
- Dữ liệu được cập nhật đúng

---

## Test Case 6: Kiểm tra persistence trong JSON

**Điều kiện tiên quyết:**
- Đã tạo action với teaching image

**Các bước thực hiện:**
1. Save tool với action có teaching image
2. Mở file JSON trong thư mục tools/
3. Tìm action vừa tạo
4. Kiểm tra các fields:
   - "image_path": "[đường dẫn]"
   - "teaching_corner_x1": [số]
   - "teaching_corner_y1": [số]
   - "teaching_corner_x2": [số]
   - "teaching_corner_y2": [số]
   - "click_x": [số] (chỉ có trong MOUSE_CLICK)
   - "click_y": [số] (chỉ có trong MOUSE_CLICK)

**Kết quả mong đợi:**
- Tất cả fields đều có trong JSON
- Giá trị không phải null (trừ khi chưa chọn ảnh)
- Đường dẫn image_path hợp lệ

---

## Các vấn đề có thể gặp

### Vấn đề 1: Label không hiển thị tên file sau khi load
**Nguyên nhân:** `_load_settings()` không gọi `_update_image_button_text()`
**Cách fix:** Đã thêm `_update_image_button_text()` vào cuối `_load_settings()`

### Vấn đề 2: Teaching corners không được save
**Nguyên nhân:** `get_settings()` không return teaching_corner fields
**Cách fix:** Đã thêm teaching_corner_x1/y1/x2/y2 vào return dict

### Vấn đề 3: Click coordinates bị mất sau khi reopen
**Nguyên nhân:** `action_config_dialog.py` không save click_x/click_y
**Cách fix:** Đã thêm save click_x/click_y trong `_open_action_settings()`

### Vấn đề 4: File ảnh không tồn tại sau khi reopen
**Nguyên nhân:** Đường dẫn tương đối không đúng
**Cách fix:** Kiểm tra đường dẫn trong JSON, phải là relative path từ root

---

## Kết luận

Sau khi test tất cả các test cases trên, nếu:
- ✅ Tất cả dữ liệu được load đúng sau khi reopen app
- ✅ File ảnh vẫn tồn tại
- ✅ Button text cập nhật đúng
- ✅ JSON chứa đầy đủ fields

→ **Teaching image feature hoạt động chính xác!**

Nếu có bất kỳ test case nào fail, vui lòng báo lại để fix.
