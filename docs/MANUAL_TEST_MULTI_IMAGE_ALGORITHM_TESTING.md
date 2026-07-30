# Manual Test Plan: Multi-Image Algorithm Testing Dialog

## Mục đích

Test dialog cho phép test nhiều window captures với teaching image để tìm preprocessing algorithm tốt nhất.

---

## Test Case 1: Mở Dialog và Hiển thị Teaching Image

**Mục đích:** Verify dialog mở đúng và hiển thị teaching image từ action settings.

**Điều kiện tiên quyết:**
- Đã có tool với action IMAGE_DETECT hoặc READ_PASSIVE
- Action đã có teaching image (image_path)

**Các bước thực hiện:**
1. Mở Tool Editor
2. Chọn action có teaching image
3. Click "Edit Settings" → Passive Read Settings Dialog
4. Click nút "🧪 Test Algorithms"

**Kết quả mong đợi:**
- Dialog mở với title "Multi-Image Algorithm Testing"
- Preview area bên trái hiển thị teaching image
- Label hiển thị "📷 Teaching Image (from action.image_path)"
- Preview area bên phải trống (chưa chọn window capture)
- Window Captures List trống
- Algorithm list hiển thị 7 algorithms mặc định

**Cài đặt cần kiểm tra:**
- action.image_path: đường dẫn đến teaching image hợp lệ

---

## Test Case 2: Load Window Captures từ Local

**Mục đích:** Verify load nhiều ảnh window capture từ local.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Có sẵn 3-5 ảnh PNG/JPG trên máy

**Các bước thực hiện:**
1. Click nút [📁 Load Images...]
2. Chọn 3-5 ảnh từ local
3. Click "Open"

**Kết quả mong đợi:**
- Tất cả ảnh được thêm vào Window Captures List
- Mỗi item hiển thị: "capture_XXX.png | Not tested yet"
- Checkbox ở trạng thái unchecked
- Ảnh được copy vào folder: `images/[tool_id]/[action_name]/window_captures/`
- Label hiển thị: "Auto-saved to: images/[tool_id]/[action_name]/window_captures/"

**Cài đặt cần kiểm tra:**
- Không có (load từ local)

---

## Test Case 3: Capture New Screenshot

**Mục đích:** Verify chụp screenshot mới từ window game.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã chọn target window (game window)

**Các bước thực hiện:**
1. Mở game window
2. Click nút [📷 Capture New]

**Kết quả mong đợi:**
- Screenshot được chụp và thêm vào list
- Ảnh được lưu vào folder: `images/[tool_id]/[action_name]/window_captures/capture_XXX.png`
- Item mới hiển thị trong list với text "capture_XXX.png | Not tested yet"

**Cài đặt cần kiểm tra:**
- target_window_hwnd: window handle của game

---

## Test Case 4: Select Window Capture và Xem Preview

**Mục đích:** Verify click vào window capture hiển thị preview bên phải.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã có ít nhất 1 window capture trong list (Test Case 2 hoặc 3)

**Các bước thực hiện:**
1. Click vào item đầu tiên trong Window Captures List

**Kết quả mong đợi:**
- Preview area bên phải hiển thị ảnh window capture đã chọn
- Ảnh được scale to fit trong preview area
- Item được highlight (selected)

**Cài đặt cần kiểm tra:**
- Không có

---

## Test Case 5: Remove Selected Window Captures

**Mục đích:** Verify xóa window captures đã chọn.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã có ít nhất 3 window captures trong list

**Các bước thực hiện:**
1. Check checkbox của 2 items đầu tiên
2. Click nút [➖ Remove Selected]

**Kết quả mong đợi:**
- 2 items được xóa khỏi list
- Số lượng items giảm đi 2
- Files ảnh vẫn còn trong folder (không xóa file)

**Cài đặt cần kiểm tra:**
- Không có

---

## Test Case 6: Test với Algorithm "None"

**Mục đích:** Verify test window captures với algorithm "None" (không preprocessing).

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã có ít nhất 3 window captures trong list
- action.match_threshold = 0.80

**Các bước thực hiện:**
1. Check checkbox của tất cả window captures
2. Chọn algorithm "None" trong dropdown "Selected Algorithm"
3. Click nút [🧪 Test Checked Images]
4. Chờ test hoàn thành

**Kết quả mong đợi:**
- Progress bar hiển thị tiến trình (0% → 100%)
- Text hiển thị: "Testing: capture_XXX.png with None... (X/Y)"
- Threshold hiển thị: "Threshold: 0.80 (from action settings)"
- Sau khi test xong, mỗi item hiển thị:
  - "capture_001.png | Match: 0.XX ✅" (nếu score >= 0.80)
  - "capture_002.png | Match: 0.XX ❌" (nếu score < 0.80)
- Item có score cao nhất được đánh dấu "⭐ BEST"
- Preview bên phải highlight vùng match (vẽ rectangle)

**Cài đặt cần kiểm tra:**
- action.match_threshold: 0.80
- action.multiscale_enabled: True/False

---

## Test Case 7: Test với Algorithm "Upscale 2x"

**Mục đích:** Verify test với preprocessing algorithm "Upscale 2x".

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã có ít nhất 3 window captures trong list

**Các bước thực hiện:**
1. Check checkbox của tất cả window captures
2. Chọn algorithm "Upscale 2x" trong dropdown
3. Click nút [🧪 Test Checked Images]
4. Chờ test hoàn thành

**Kết quả mong đợi:**
- Test chạy với preprocessing: teaching image được upscale 2x trước khi match
- Kết quả hiển thị tương tự Test Case 6
- Score có thể khác so với "None" algorithm

**Cài đặt cần kiểm tra:**
- Không có (algorithm hardcoded)

---

## Test Case 8: Test với Algorithm "Full Pipeline"

**Mục đích:** Verify test với full preprocessing pipeline.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã có ít nhất 3 window captures trong list

**Các bước thực hiện:**
1. Check checkbox của tất cả window captures
2. Chọn algorithm "Full Pipeline" trong dropdown
3. Click nút [🧪 Test Checked Images]
4. Chờ test hoàn thành

**Kết quả mong đợi:**
- Test chạy với full preprocessing: Upscale 2x + Contrast + Sharpen + Denoise
- Kết quả hiển thị tương tự Test Case 6
- Score có thể cao hơn so với "None" hoặc "Upscale 2x"

**Cài đặt cần kiểm tra:**
- Không có (algorithm hardcoded)

---

## Test Case 9: Stop Test đang chạy

**Mục đích:** Verify dừng test đang chạy.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã có ít nhất 10 window captures trong list

**Các bước thực hiện:**
1. Check checkbox của tất cả window captures
2. Chọn algorithm bất kỳ
3. Click nút [🧪 Test Checked Images]
4. Ngay sau khi test bắt đầu, click nút [⏸️ Stop]

**Kết quả mong đợi:**
- Test dừng lại ngay lập tức
- Progress bar dừng ở vị trí hiện tại
- Các items đã test hiển thị kết quả
- Các items chưa test vẫn hiển thị "Not tested yet"
- Nút Test được enable lại

**Cài đặt cần kiểm tra:**
- Không có

---

## Test Case 10: Add Algorithm vào List

**Mục đích:** Verify thêm algorithm vào list quản lý.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)

**Các bước thực hiện:**
1. Chọn "Upscale 2x" trong dropdown ở Algorithm Management section
2. Click nút [➕ Add]

**Kết quả mong đợi:**
- Algorithm "Upscale 2x" được thêm vào list
- List hiển thị item mới với text "Upscale 2x"
- Item có 2 nút: [⚙️ Settings] [❌ Delete]

**Cài đặt cần kiểm tra:**
- Không có

---

## Test Case 11: Delete Algorithm khỏi List

**Mục đích:** Verify xóa algorithm khỏi list quản lý.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã add ít nhất 1 algorithm vào list (Test Case 10)

**Các bước thực hiện:**
1. Click nút [❌ Delete] của algorithm vừa add

**Kết quả mong đợi:**
- Algorithm bị xóa khỏi list
- Số lượng items trong list giảm đi 1

**Cài đặt cần kiểm tra:**
- Không có

---

## Test Case 12: Click Settings Button (Coming Soon)

**Mục đích:** Verify click Settings button hiển thị message "Tính năng đang phát triển".

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã add ít nhất 1 algorithm vào list (Test Case 10)

**Các bước thực hiện:**
1. Click nút [⚙️ Settings] của algorithm bất kỳ

**Kết quả mong đợi:**
- Message box hiển thị: "Tính năng đang phát triển"
- Click OK để đóng message box

**Cài đặt cần kiểm tra:**
- Không có

---

## Test Case 13: Click OK để Lưu Data

**Mục đích:** Verify click OK lưu tất cả data vào action.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã load 3 window captures (Test Case 2)
- Đã test với algorithm (Test Case 6)
- Đã add 2 algorithms vào list (Test Case 10)

**Các bước thực hiện:**
1. Click nút [✅ OK]
2. Dialog đóng
3. Mở lại dialog (Test Case 1)

**Kết quả mong đợi:**
- Dialog đóng và return accepted
- Data được lưu vào action:
  - action.window_capture_paths: list 3 đường dẫn
  - action.window_capture_results: dict {path: score}
  - action.preprocessing_algorithms: list 2 algorithm configs
- Khi mở lại dialog:
  - Window Captures List hiển thị 3 items với kết quả test
  - Algorithm list hiển thị 2 algorithms đã add

**Cài đặt cần kiểm tra:**
- action.window_capture_paths: list[str]
- action.window_capture_results: dict[str, float]
- action.preprocessing_algorithms: list[dict]

---

## Test Case 14: Click Close để Không Lưu

**Mục đích:** Verify click Close không lưu data.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã load 3 window captures (Test Case 2)
- Đã test với algorithm (Test Case 6)

**Các bước thực hiện:**
1. Click nút [❌ Close]
2. Dialog đóng
3. Mở lại dialog (Test Case 1)

**Kết quả mong đợi:**
- Dialog đóng và return rejected
- Data KHÔNG được lưu vào action
- Khi mở lại dialog:
  - Window Captures List trống (hoặc hiển thị data cũ nếu có)
  - Test results không có

**Cài đặt cần kiểm tra:**
- action.window_capture_paths: không thay đổi
- action.window_capture_results: không thay đổi

---

## Test Case 15: Data Persistence (Save Tool → Reload)

**Mục đích:** Verify data được lưu đúng vào JSON và load lại đúng.

**Điều kiện tiên quyết:**
- Đã hoàn thành Test Case 13 (click OK để lưu data)

**Các bước thực hiện:**
1. Click "Save Tool" trong Tool Editor
2. Đóng Tool Editor
3. Đóng app
4. Mở lại app
5. Load tool vừa save
6. Mở action settings → Click "🧪 Test Algorithms"

**Kết quả mong đợi:**
- Dialog mở với data đã lưu:
  - Window Captures List hiển thị đúng các items
  - Test results hiển thị đúng scores
  - Algorithm list hiển thị đúng algorithms đã add
- Verify file JSON:
  - action.window_capture_paths: array of strings
  - action.window_capture_results: object {path: score}
  - action.preprocessing_algorithms: array of objects

**Cài đặt cần kiểm tra:**
- Kiểm tra file JSON trong folder tools/

---

## Test Case 16: Max 50 Window Captures

**Mục đích:** Verify giới hạn tối đa 50 window captures.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)

**Các bước thực hiện:**
1. Load 60 ảnh từ local (hoặc capture 60 screenshots)

**Kết quả mong đợi:**
- Chỉ 50 ảnh đầu tiên được thêm vào list
- 10 ảnh sau bị bỏ qua
- Message box cảnh báo: "Đã đạt giới hạn 50 window captures"

**Cài đặt cần kiểm tra:**
- Không có

---

## Test Case 17: Teaching Image Not Found

**Mục đích:** Verify xử lý khi teaching image không tồn tại.

**Điều kiện tiên quyết:**
- Đã có tool với action IMAGE_DETECT
- action.image_path = None hoặc đường dẫn không tồn tại

**Các bước thực hiện:**
1. Mở Tool Editor
2. Chọn action không có teaching image
3. Click "Edit Settings" → Passive Read Settings Dialog
4. Click nút "🧪 Test Algorithms"

**Kết quả mong đợi:**
- Dialog mở nhưng hiển thị warning:
  - Message box: "Teaching image không tồn tại! Vui lòng chọn teaching image trước."
- Các nút bị disable:
  - [📁 Load Images...] disabled
  - [📷 Capture New] disabled
  - [🧪 Test Checked Images] disabled

**Cài đặt cần kiểm tra:**
- action.image_path: None hoặc invalid path

---

## Test Case 18: Thread-Safe UI Updates (Spam Click Stop)

**Mục đích:** Verify UI updates thread-safe, không crash khi spam click.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã có ít nhất 10 window captures trong list

**Các bước thực hiện:**
1. Check checkbox của tất cả window captures
2. Chọn algorithm "Full Pipeline" (chậm nhất)
3. Click nút [🧪 Test Checked Images]
4. Spam click nút [⏸️ Stop] nhiều lần liên tục (10-20 lần)

**Kết quả mong đợi:**
- App KHÔNG crash
- Test dừng lại đúng cách
- UI vẫn responsive
- Không có error trong console

**Cài đặt cần kiểm tra:**
- Không có (test thread-safety)

---

## Test Case 19: Compare với Threshold từ Action Settings

**Mục đích:** Verify kết quả test so sánh đúng với threshold từ action settings.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- action.match_threshold = 0.85
- Đã có window captures với scores khác nhau

**Các bước thực hiện:**
1. Test window captures với algorithm bất kỳ
2. Xem kết quả trong list

**Kết quả mong đợi:**
- Items với score >= 0.85 hiển thị ✅
- Items với score < 0.85 hiển thị ❌
- Threshold label hiển thị: "Threshold: 0.85 (from action settings)"

**Cài đặt cần kiểm tra:**
- action.match_threshold: 0.85

---

## Test Case 20: Best Score Highlighting

**Mục đích:** Verify ảnh có score cao nhất được đánh dấu ⭐.

**Điều kiện tiên quyết:**
- Dialog đã mở (Test Case 1)
- Đã test ít nhất 3 window captures với scores khác nhau

**Các bước thực hiện:**
1. Xem kết quả trong Window Captures List

**Kết quả mong đợi:**
- Item có score cao nhất hiển thị "⭐ BEST" hoặc "⭐"
- Chỉ có 1 item được đánh dấu BEST
- Nếu có nhiều items cùng score cao nhất, chỉ item đầu tiên được đánh dấu

**Cài đặt cần kiểm tra:**
- Không có

---

## Tổng kết

**Tổng số test cases:** 20

**Phân loại:**
- UI/UX: 8 test cases (1, 2, 3, 4, 5, 10, 11, 12)
- Testing Logic: 6 test cases (6, 7, 8, 9, 19, 20)
- Data Management: 4 test cases (13, 14, 15, 16)
- Error Handling: 2 test cases (17, 18)

**Thời gian ước tính:** 60-90 phút

**Lưu ý:**
- Test trên Windows với game window thật
- Chuẩn bị sẵn 10-20 ảnh PNG/JPG để test load
- Test với nhiều loại teaching images (text, icons, UI elements)
- Test với nhiều resolutions khác nhau
