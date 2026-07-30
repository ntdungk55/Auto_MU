# Manual Test Plan: Template Mask Regions

## Mục đích
Kiểm tra tính năng vẽ mask regions để bỏ qua vùng text động khi template matching.

---

## Test Case 1: Vẽ mask regions cơ bản

**Điều kiện tiên quyết:**
- App đang chạy
- Đã chọn window game
- Có tool với action IMAGE_DETECT hoặc MOUSE_CLICK

**Các bước thực hiện:**
1. Mở tool editor
2. Chọn action IMAGE_DETECT
3. Click "⚙️ Cài đặt"
4. Click "Tạo ảnh Teaching"
5. Chụp ảnh có vùng text động
6. Crop vùng cần thiết
7. **Click button "Vẽ Mask"** (button mới)
8. **Vẽ hình chữ nhật bao quanh vùng text** (drag mouse)
9. Verify: Hình chữ nhật màu đỏ semi-transparent hiển thị
10. **Vẽ thêm 2-3 mask regions khác**
11. Verify: Tất cả mask regions hiển thị rõ ràng
12. Click "OK"

**Kết quả mong đợi:**
- Button "Vẽ Mask" hoạt động
- Vẽ được nhiều mask regions
- Mask regions màu đỏ, trong suốt, thấy ảnh bên dưới
- Mask regions được lưu vào action

---

## Test Case 2: Xóa mask regions

**Điều kiện tiên quyết:**
- Đã vẽ 3-4 mask regions (từ Test Case 1)

**Các bước thực hiện:**
1. **Click vào mask region thứ 2**
2. Verify: Mask được highlight (viền dày hơn)
3. **Nhấn Delete key**
4. Verify: Mask region bị xóa
5. **Chuột phải vào mask region thứ 3**
6. Verify: Context menu hiện "Xóa mask"
7. Click "Xóa mask"
8. Verify: Mask region bị xóa
9. **Click button "Xóa tất cả mask"**
10. Verify: Tất cả mask regions bị xóa

**Kết quả mong đợi:**
- Click vào mask → highlight
- Delete key → xóa mask đã select
- Chuột phải → menu "Xóa mask" → xóa
- Button "Xóa tất cả" → xóa hết

---

## Test Case 3: Save và Load mask regions

**Điều kiện tiên quyết:**
- Đã vẽ 2-3 mask regions

**Các bước thực hiện:**
1. Vẽ 2 mask regions trên teaching image
2. Click "OK" để đóng ImageCaptureDialog
3. Click "Lưu" để lưu action
4. **Đóng app**
5. **Mở lại app**
6. Mở tool vừa save
7. Chọn action vừa tạo
8. Click "⚙️ Cài đặt"
9. Click "Xem/Sửa ảnh Teaching"
10. Verify: 2 mask regions hiển thị đúng vị trí

**Kết quả mong đợi:**
- Mask regions được save vào JSON
- Load lại app → mask regions hiển thị đúng
- Tọa độ và kích thước mask không thay đổi

---

## Test Case 4: Template matching với mask - Text thay đổi

**Điều kiện tiên quyết:**
- Có teaching image với vùng text động
- Đã vẽ mask bao quanh vùng text

**Các bước thực hiện:**
1. Tạo action IMAGE_DETECT với teaching image có text "ABC"
2. Vẽ mask bao quanh text "ABC"
3. Set threshold = 0.8 (cao)
4. Save action
5. **Thay đổi text trong game thành "XYZ"** (cùng vị trí)
6. Chạy action
7. Verify: Action tìm thấy ảnh (score >= 0.8)
8. Check log: Score cao (>= 0.8)

**Kết quả mong đợi:**
- Threshold cao (0.8) vẫn match được
- Text thay đổi không ảnh hưởng score
- Tìm đúng vị trí ảnh

---

## Test Case 5: Template matching với mask - So sánh có/không mask

**Điều kiện tiên quyết:**
- Có teaching image với vùng text động

**Các bước thực hiện:**
1. Tạo 2 actions giống nhau:
   - Action A: Không có mask, threshold = 0.6
   - Action B: Có mask bao text, threshold = 0.8
2. **Thay đổi text trong game**
3. Chạy Action A
4. Check log: Score thấp (< 0.7)
5. Chạy Action B
6. Check log: Score cao (>= 0.8)

**Kết quả mong đợi:**
- Action A (không mask): Score thấp khi text thay đổi
- Action B (có mask): Score cao khi text thay đổi
- Mask giúp tăng độ chính xác

---

## Test Case 6: Mask quá nhiều vùng

**Điều kiện tiên quyết:**
- Teaching image 100x100 pixels

**Các bước thực hiện:**
1. Vẽ mask regions phủ > 90% ảnh
2. Click "OK"
3. Verify: Warning "Mask quá nhiều, phải còn ít nhất 10% để match"
4. Xóa bớt mask
5. Click "OK"
6. Verify: Lưu thành công

**Kết quả mong đợi:**
- Validation: Không cho mask > 90% ảnh
- Warning message rõ ràng
- Phải xóa bớt mask mới lưu được

---

## Test Case 7: Backward compatibility

**Điều kiện tiên quyết:**
- Có tool cũ (không có mask_regions)

**Các bước thực hiện:**
1. Load tool cũ (tạo trước khi có feature mask)
2. Chạy action IMAGE_DETECT
3. Verify: Action chạy bình thường
4. Check log: Không có error về mask_regions

**Kết quả mong đợi:**
- Tool cũ vẫn chạy được
- Không breaking changes
- mask_regions = None hoặc [] → matching bình thường

---

## Cài đặt cần kiểm tra

**ImageCaptureDialog:**
- Button "Vẽ Mask" hiển thị
- Chế độ vẽ mask hoạt động
- Mask regions màu đỏ, alpha = 0.3
- Selected mask có viền dày 3px
- Context menu "Xóa mask"
- Button "Xóa tất cả mask"

**AutoAction:**
- Field mask_regions: list[dict]
- Format: [{"x": int, "y": int, "w": int, "h": int}]

**Template Matching:**
- Tạo mask array từ mask_regions
- cv2.matchTemplate() với mask parameter
- Score cao hơn khi có mask

---

## Lưu ý

- Mask regions tọa độ relative to teaching image (không phải screen)
- Mask regions lưu trong action JSON
- Validation: Mask không được > 90% ảnh
- Performance: Mask array được cache
